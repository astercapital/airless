
import os
import logging
from datetime import datetime, timedelta
import shutil
import copy

from google.api_core.exceptions import NotFound
import pyarrow as pa
from pyarrow import parquet, json as pa_json
from pyarrow import fs

from airless.config import get_config
from airless.hook.google.bigquery import BigqueryHook
from airless.hook.google.storage import GcsHook
from airless.hook.file.file import FileHook
from airless.operator.base import BaseFileOperator, BaseEventOperator


class ProcessTopic:
    SMALL = 'PUBSUB_TOPIC_FILE_BATCH_AGGREGATE_PROCESS_SMALL'
    MEDIUM = 'PUBSUB_TOPIC_FILE_BATCH_AGGREGATE_PROCESS_MEDIUM'
    LARGE = 'PUBSUB_TOPIC_FILE_BATCH_AGGREGATE_PROCESS_LARGE'


class FileDetectOperator(BaseFileOperator):

    def __init__(self):
        super().__init__()
        self.gcs_hook = GcsHook()

    def execute(self, bucket, filepath):
        success_messages = self.build_success_message(bucket, filepath)

        for success_message in success_messages:
            self.pubsub_hook.publish(
                project=get_config('GCP_PROJECT'),
                topic=get_config('PUBSUB_TOPIC_FILE_TO_BQ'),
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


class FileToBigqueryOperator(BaseEventOperator):

    def __init__(self):
        super().__init__()
        self.gcs_hook = GcsHook()
        self.bigquery_hook = BigqueryHook()

    def execute(self, data, topic):
        metadata = data['metadata']
        file_format = metadata['file_format']

        if file_format in ('csv', 'json'):
            self.bigquery_hook.load_file(
                from_filepath=self.gcs_hook.build_filepath(metadata['bucket'], metadata['file']),
                from_file_format=file_format,
                from_separator=metadata.get('separator'),
                from_skip_leading_rows=metadata.get('skip_leading_rows'),
                from_quote_character=metadata.get('quote_character'),
                from_encoding=metadata.get('encoding'),
                to_project=get_config('GCP_PROJECT'),
                to_dataset=metadata['destination_dataset'],
                to_table=metadata['destination_table'],
                to_mode=metadata['mode'],
                to_schema=metadata.get('schema'),
                to_time_partitioning=metadata.get('time_partitioning'))

        else:
            raise Exception(f'File format {file_format} load not implemented')


class BatchWriteDetectOperator(BaseEventOperator):
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
        self.pubsub_hook.publish(
            project=get_config('GCP_PROJECT'),
            topic=get_config('PUBSUB_TOPIC_BATCH_WRITE_PROCESS'),
            data={'bucket': bucket, 'directory': directory, 'files': files})


class BatchWriteDetectAggregateOperator(BaseEventOperator):

    def __init__(self):
        super().__init__()
        self.file_hook = FileHook()
        self.gcs_hook = GcsHook()
        self.reprocess = False

    def execute(self, data, topic):
        bucket = data.get('bucket', get_config('GCS_BUCKET_LANDING_ZONE'))
        prefix = data.get('prefix')
        threshold = data['threshold']
        reprocess_delay = threshold.get('reprocess_delay', 60)
        reprocess_max_times = threshold.get('reprocess_max_times', 0)
        reprocess_time = data.get('metadata', {}).get('reprocess_time', 0)

        tables = {}
        partially_processed_tables = []

        for b in self.gcs_hook.list(bucket, prefix):
            # Verify if blob is not deleted
            if (b.time_deleted is None):
                filepaths = b.name.split('/')
                key = '/'.join(filepaths[:-1])  # dataset/table
                filename = filepaths[-1]

                if (b.size < threshold['size_medium']):  # size less than best performance partition size

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

                    # Try to create the best performance partition size
                    if tables[key]['size'] > threshold['size_medium']:
                        self.send_to_process(from_bucket=bucket, to_bucket=get_config('GCS_BUCKET_RAW_ZONE'), directory=key, files=tables[key]['files'], size=ProcessTopic.MEDIUM)
                        tables[key] = None
                        partially_processed_tables.append(key)
                    else:
                        # If number of files is too high process it
                        if (len(tables[key]['files']) > threshold['file_quantity']):
                            self.send_to_process(
                                from_bucket=bucket,
                                to_bucket=bucket,
                                directory=key,
                                files=tables[key]['files'],
                                size=ProcessTopic.SMALL if tables[key]['size'] < threshold['size_small'] else ProcessTopic.MEDIUM)
                            tables[key] = None
                            partially_processed_tables.append(key)
                else:
                    self.send_to_process(from_bucket=bucket, to_bucket=get_config('GCS_BUCKET_RAW_ZONE'), directory=key, files=[filename], size=ProcessTopic.MEDIUM)

        # verify which dataset/table is ready to be processed
        time_threshold = (datetime.now() - timedelta(minutes=threshold['minutes'])).strftime('%Y-%m-%d %H:%M')
        for directory, v in tables.items():
            if v is not None:
                if (len(v['files']) == 1) and (directory not in partially_processed_tables):
                    # only have one file that is lower than best performnce partition size in this directory
                    self.send_to_process(
                        from_bucket=bucket,
                        to_bucket=get_config('GCS_BUCKET_RAW_ZONE'),
                        directory=key,
                        files=v['files'],
                        size=ProcessTopic.SMALL if v['size'] < threshold['size_small'] else ProcessTopic.MEDIUM)
                elif ((directory in partially_processed_tables) or (v['min_time_created'].strftime('%Y-%m-%d %H:%M') < time_threshold)):
                    self.send_to_process(
                        from_bucket=bucket,
                        to_bucket=bucket,
                        directory=directory,
                        files=v['files'],
                        size=ProcessTopic.SMALL if v['size'] < threshold['size_small'] else ProcessTopic.MEDIUM)

        # Reprocess data until only one file can be lower than best performance partition size
        if self.reprocess and reprocess_time < reprocess_max_times:
            self.send_to_reprocess(reprocess_delay, topic, data)

    def send_to_process(self, from_bucket, to_bucket, directory, files, size):
            self.pubsub_hook.publish(
                project=get_config('GCP_PROJECT'),
                topic=get_config(size),
                data={'from_bucket': from_bucket, 'to_bucket': to_bucket, 'directory': directory, 'files': files})

            self.reprocess = True

    def send_to_reprocess(self, reprocess_delay, topic, data):
        reprocess_data = copy.deepcopy(data)
        reprocess_data['threshold']['minutes'] = 0  # Change to zero because new files were aggreagated

        if reprocess_data.get('metadata'):
            reprocess_data['metadata']['reprocess_time'] += 1
        else:
            reprocess_data['metadata'] = {}
            reprocess_data['metadata']['reprocess_time'] = 1

        self.pubsub_hook.publish(
            project=get_config('GCP_PROJECT'),
            topic=get_config('PUBSUB_DELAY_TOPIC'),
            data={'seconds': reprocess_delay, 'metadata': {'run_next': [{'topic': topic, 'data': reprocess_data}]}})


class BatchWriteProcessOperator(BaseEventOperator):

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

        self.move_files(from_bucket, get_config('GCS_BUCKET_LANDING_ZONE_PROCESSED'), directory, files)

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

    def move_files(self, from_bucket, to_bucket, directory, files):
        for f in files:
            self.gcs_hook.move(
                from_bucket=from_bucket,
                from_prefix=f'{directory}/{f}',
                to_bucket=to_bucket,
                to_directory=directory)


class BatchAggregateParquetFilesOperator(BaseEventOperator):
    def __init__(self):
        super().__init__()
        self.file_hook = FileHook()
        self.gcs_hook = GcsHook()
        self.fs_gcs = fs.GcsFileSystem()

    def execute(self, data, topic):
        from_bucket = data['from_bucket']
        to_bucket = data['to_bucket']
        directory = data['directory']
        files = data['files']

        # Read parquets from gcs
        tables_union = self.read_parquet_from_gcs(from_bucket, directory, files)

        # Save parquet concatenated
        local_filename = self.file_hook.get_tmp_filepath('tmp.parquet', add_timestamp=True)
        local_filename = local_filename.split('/')[-1]
        parquet.write_table(
            tables_union,
            f'{to_bucket}/{directory}/{local_filename}',
            compression='GZIP',
            filesystem=self.fs_gcs
        )

        self.send_to_delete(from_bucket, directory, files)

    def read_parquet_from_gcs(self, bucket, directory, files):
        concat = None
        for f in files:
            t = parquet.read_table(f'{bucket}/{directory}/{f}', filesystem=self.fs_gcs)
            concat = t if not concat else pa.concat_tables([t,concat])

        return concat

    def send_to_delete(self, from_bucket, directory, files):
        obj = {
            'bucket': from_bucket,
            'files': [f'{directory}/{f}' for f in files]
        }

        self.pubsub_hook.publish(
            project=get_config('GCP_PROJECT'),
            topic=get_config('PUBSUB_TOPIC_GCS_DELETE'),
            data=obj)


class FileDeleteOperator(BaseEventOperator):

    def __init__(self):
        super().__init__()
        self.gcs_hook = GcsHook()

    def execute(self, data, topic):
        bucket = data['bucket']
        prefix = data.get('prefix')
        files = data.get('files', [])

        if (prefix is None) and (not files):
            raise Exception('prefix or files parameter has to be defined!')

        logging.info(f'Deleting from bucket {bucket}')
        self.gcs_hook.delete(bucket, prefix, files)


class FileMoveOperator(BaseEventOperator):

    def __init__(self):
        super().__init__()
        self.gcs_hook = GcsHook()

    def execute(self, data, topic):
        origin_bucket = data['origin']['bucket']
        origin_prefix = data['origin']['prefix']
        dest_bucket = data['destination']['bucket']
        dest_directory = data['destination']['directory']
        self.gcs_hook.move(origin_bucket, origin_prefix, dest_bucket, dest_directory, True)
