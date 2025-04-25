
import os

from datetime import datetime, timedelta
from deprecation import deprecated
from google.api_core.exceptions import NotFound

from airless.core.utils import get_config
from airless.core.hook import FileHook
from airless.google.cloud.core.operator import GoogleBaseFileOperator, GoogleBaseEventOperator
from airless.google.cloud.storage.hook import GcsHook


class FileDetectOperator(GoogleBaseFileOperator):

    def __init__(self):
        super().__init__()
        self.gcs_hook = GcsHook()

    def execute(self, bucket, filepath):
        success_messages = self.build_success_message(bucket, filepath)

        for success_message in success_messages:
            self.queue_hook.publish(
                project=get_config('GCP_PROJECT'),
                topic=get_config('QUEUE_TOPIC_FILE_TO_BQ'),
                data=success_message)

    def build_success_message(self, bucket, filepath):
        dataset, table, mode, separator, skip_leading_rows, \
            file_format, schema, run_next, quote_character, encoding, \
            column_names, time_partitioning, processing_method, \
            gcs_table_name, sheet_name, arguments, options = self.get_ingest_config(filepath)

        metadatas = []
        for idx in range(len(file_format)):
            metadatas.append({
                'metadata': {
                    'destination_dataset': dataset,
                    'destination_table': table,
                    'file_format': file_format[idx],
                    'mode': mode,
                    'bucket': bucket,
                    'file': filepath,
                    'separator': separator[idx],
                    'skip_leading_rows': skip_leading_rows[idx],
                    'quote_character': quote_character[idx],
                    'encoding': encoding[idx],
                    'schema': schema[idx],
                    'run_next': run_next[idx],
                    'column_names': column_names[idx],
                    'time_partitioning': time_partitioning[idx],
                    'processing_method': processing_method[idx],
                    'gcs_table_name': gcs_table_name[idx],
                    'sheet_name': sheet_name[idx],
                    'arguments': arguments[idx],
                    'options': options[idx]
                }
            })

        return metadatas

    def get_ingest_config(self, filepath):
        dataset, table, mode = self.split_filepath(filepath)

        metadata = self.read_config_file(dataset, table)

        # Verifying if config file hava multiple configs or not
        if isinstance(metadata, list):
            metadata = metadata
        elif isinstance(metadata, dict):
            metadata = [metadata]
        else:
            raise NotImplementedError()

        # Instanciate all values
        # inputs
        file_format = []
        separator = []
        skip_leading_rows = []
        quote_character = []
        encoding = []
        sheet_name = []
        arguments = []
        options = []

        # outputs
        schema = []
        column_names = []
        time_partitioning = []
        processing_method = []
        gcs_table_name = []
        run_next = []

        for config in metadata:
            # input
            file_format.append(config.get('file_format', 'csv'))
            separator.append(config.get('separator'))
            skip_leading_rows.append(config.get('skip_leading_rows'))
            quote_character.append(config.get('quote_character'))
            encoding.append(config.get('encoding', None))
            sheet_name.append(config.get('sheet_name', None))
            arguments.append(config.get('arguments', None))
            options.append(config.get('options', None))

            # output
            schema.append(config.get('schema', None))
            column_names.append(config.get('column_names', None))
            time_partitioning.append(config.get('time_partitioning', None))
            processing_method.append(config.get('processing_method', None))
            gcs_table_name.append(config.get('gcs_table_name', None))

            # after processing
            run_next.append(config.get('run_next', []))

        return dataset, table, mode, separator, \
            skip_leading_rows, file_format, schema, \
            run_next, quote_character, encoding, column_names, \
            time_partitioning, processing_method, gcs_table_name, \
            sheet_name, arguments, options

    def split_filepath(self, filepath):
        filepath_array = filepath.split('/')
        if len(filepath_array) < 3:
            raise Exception('Invalid file path. Must be added to directory {dataset}/{table}/{mode}')

        dataset = filepath_array[0]
        table = filepath_array[1]
        mode = filepath_array[2]
        return dataset, table, mode

    def read_config_file(self, dataset, table):
        try:
            config = self.gcs_hook.read_json(
                bucket=get_config('GCS_BUCKET_LANDING_ZONE_LOADER_CONFIG'),
                filepath=f'{dataset}/{table}.json')
            return config
        except NotFound:
            return {'file_format': 'json', 'time_partitioning': {'type': 'DAY', 'field': '_created_at'}}


@deprecated(deprecated_in="0.0.5", removed_in="1.0.0",
            details="This class will be deprecated. Please write files directly to datalake using `GcsDatalakeHook`")
class BatchWriteDetectOperator(GoogleBaseEventOperator):
    # Will be deprecreated

    def __init__(self):
        super().__init__()
        self.file_hook = FileHook()
        self.gcs_hook = GcsHook()

    def execute(self, data, topic):
        bucket = data.get('bucket', get_config('GCS_BUCKET_LANDING_ZONE'))
        prefix = data.get('prefix')
        threshold = data['threshold']

        tables = {}
        partially_processed_tables = []

        for b in self.gcs_hook.list(bucket, prefix):
            if b.time_deleted is None:
                filepaths = b.name.split('/')
                key = '/'.join(filepaths[:-1])  # dataset/table
                filename = filepaths[-1]

                if tables.get(key) is None:
                    tables[key] = {
                        'size': b.size,
                        'files': [filename],
                        'min_time_created': b.time_created
                    }
                else:
                    tables[key]['size'] += b.size
                    tables[key]['files'] += [filename]
                    if b.time_created < tables[key]['min_time_created']:
                        tables[key]['min_time_created'] = b.time_created

                if (tables[key]['size'] > threshold['size']) or (len(tables[key]['files']) > threshold['file_quantity']):
                    self.send_to_process(bucket=bucket, directory=key, files=tables[key]['files'])
                    tables[key] = None
                    partially_processed_tables.append(key)

        # verify which dataset/table is ready to be processed
        time_threshold = (datetime.now() - timedelta(minutes=threshold['minutes'])).strftime('%Y-%m-%d %H:%M')
        for directory, v in tables.items():
            if v is not None:
                if (v['size'] > threshold['size']) or \
                    (v['min_time_created'].strftime('%Y-%m-%d %H:%M') < time_threshold) or \
                        (len(v['files']) > threshold['file_quantity']) or \
                        (directory in partially_processed_tables):
                    self.send_to_process(bucket=bucket, directory=directory, files=v['files'])

    def send_to_process(self, bucket, directory, files):
        self.queue_hook.publish(
            project=get_config('GCP_PROJECT'),
            topic=get_config('PUBSUB_TOPIC_BATCH_WRITE_PROCESS'),
            data={'bucket': bucket, 'directory': directory, 'files': files})


@deprecated(deprecated_in="0.0.5", removed_in="1.0.0",
            details="This class will be deprecated. Please write files directly to datalake using `GcsDatalakeHook`")
class BatchWriteProcessOperator(GoogleBaseEventOperator):

    def __init__(self):
        super().__init__()
        self.file_hook = FileHook()
        self.gcs_hook = GcsHook()

    def execute(self, data, topic):
        from_bucket = data['bucket']
        directory = data['directory']
        files = data['files']

        file_contents = self.read_files(from_bucket, directory, files)

        local_filepath = self.merge_files(file_contents)

        self.gcs_hook.upload(local_filepath, get_config('GCS_BUCKET_LANDING_ZONE_LOADER'), f'{directory}/append')
        os.remove(local_filepath)

        file_paths = [directory + '/' + f for f in files]

        self.gcs_hook.move_files(
            from_bucket=from_bucket,
            files=file_paths,
            to_bucket=get_config('GCS_BUCKET_LANDING_ZONE_PROCESSED'),
            to_directory=directory,
            rewrite=False
        )

    def read_files(self, bucket, directory, files):
        file_contents = []
        for f in files:
            obj = self.gcs_hook.read_json(
                bucket=bucket,
                filepath=f'{directory}/{f}')
            if isinstance(obj, list):
                file_contents += obj
            elif isinstance(obj, dict):
                file_contents.append(obj)
            else:
                raise Exception(f'Cannot process file {directory}/{f}')
        return file_contents

    def merge_files(self, file_contents):
        local_filepath = self.file_hook.get_tmp_filepath('merged.ndjson', add_timestamp=True)
        self.file_hook.write(local_filepath=local_filepath, data=file_contents, use_ndjson=True)
        return local_filepath


class FileDeleteOperator(GoogleBaseEventOperator):

    def __init__(self):
        super().__init__()
        self.gcs_hook = GcsHook()

    def execute(self, data, topic):
        bucket = data['bucket']
        prefix = data.get('prefix')
        files = data.get('files', [])

        if (prefix is None) and (not files):
            raise Exception('prefix or files parameter has to be defined!')

        self.logger.info(f'Deleting from bucket {bucket}')
        self.gcs_hook.delete(bucket, prefix, files)


class FileMoveOperator(GoogleBaseEventOperator):

    def __init__(self):
        super().__init__()
        self.gcs_hook = GcsHook()

    def execute(self, data, topic):
        origin_bucket = data['origin']['bucket']
        origin_prefix = data['origin']['prefix']
        dest_bucket = data['destination']['bucket']
        dest_directory = data['destination']['directory']
        self.gcs_hook.move(origin_bucket, origin_prefix, dest_bucket, dest_directory, True)
