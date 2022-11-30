
from google.api_core.exceptions import NotFound

from airless.config import get_config
from airless.hook.google.bigquery import BigqueryHook
from airless.hook.google.storage import GcsHook
from airless.operator.base import BaseFileOperator, BaseEventOperator


class FileDetectOperator(BaseFileOperator):

    def __init__(self):
        super().__init__()
        self.gcs_hook = GcsHook()

    def execute(self, bucket, filepath):
        success_message = self.build_success_message(bucket, filepath)
        self.pubsub_hook.publish(
            project=get_config('GCP_PROJECT'),
            topic=get_config('PUBSUB_TOPIC_FILE_TO_BQ'),
            data=success_message)

    def build_success_message(self, bucket, filepath):
        dataset, table, mode, separator, skip_leading_rows, \
            file_format, schema, run_next, quote_character, encoding, \
            column_names, time_partitioning, processing_method, \
            gcs_table_name = self.get_ingest_config(filepath)

        return {
            'metadata': {
                'destination_dataset': dataset,
                'destination_table': table,
                'file_format': file_format,
                'mode': mode,
                'bucket': bucket,
                'file': filepath,
                'separator': separator,
                'skip_leading_rows': skip_leading_rows,
                'quote_character': quote_character,
                'encoding': encoding,
                'schema': schema,
                'run_next': run_next,
                'column_names': column_names,
                'time_partitioning': time_partitioning,
                'processing_method': processing_method,
                'gcs_table_name': gcs_table_name
            }
        }

    def get_ingest_config(self, filepath):
        dataset, table, mode = self.split_filepath(filepath)

        metadata = self.read_config_file(dataset, table)

        # input
        file_format = metadata.get('file_format', 'csv')
        separator = metadata.get('separator')
        skip_leading_rows = metadata.get('skip_leading_rows')
        quote_character = metadata.get('quote_character')
        encoding = metadata.get('encoding', None)

        # output
        schema = metadata.get('schema', None)
        column_names = metadata.get('column_names', None)
        time_partitioning = metadata.get('time_partitioning', None)
        processing_method = metadata.get('processing_method', None)
        gcs_table_name = metadata.get('gcs_table_name', None)

        # after processing
        run_next = metadata.get('run_next', [])

        return dataset, table, mode, separator, \
            skip_leading_rows, file_format, schema, \
            run_next, quote_character, encoding, column_names, \
            time_partitioning, processing_method, gcs_table_name

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
                bucket=get_config('GCS_BUCKET_FILE_ENTRANCE_CONFIG'),
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
