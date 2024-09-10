
import json
import re

from datetime import datetime
from unidecode import unidecode

from airless.core.config import get_config
from airless.core.dto import BaseDto

from airless.google.cloud.core.operator import GoogleBaseEventOperator
from airless.google.cloud.bigquery.hook import BigqueryHook
from airless.google.cloud.storage.hook import GcsHook


class GcsQueryToBigqueryOperator(GoogleBaseEventOperator):

    def __init__(self):
        super().__init__()

        self.gcs_hook = GcsHook()
        self.bigquery_hook = BigqueryHook()

    def execute(self, data, topic):

        query = data['query']
        if isinstance(query, dict):
            query_bucket = query.get('bucket', get_config('GCS_BUCKET_SQL'))
            query_filepath = query['filepath']
            query_params = query.get('params', {})
        else:
            query_bucket = get_config('GCS_BUCKET_SQL')
            query_filepath = query
            query_params = data.get('params', {})

        to = data.get('to', {})

        if to:
            to_project = to.get('project', get_config('GCP_PROJECT'))
            to_dataset = to.get('dataset')
            to_table = to.get('table')
            to_write_disposition = to.get('write_disposition')
            to_time_partitioning = to.get('time_partitioning')
        else:
            to_project = get_config('GCP_PROJECT')
            to_dataset = data.get('destination_dataset')
            to_table = data.get('destination_table')
            to_write_disposition = data.get('write_disposition')
            to_time_partitioning = data.get('time_partitioning')

        sql = self.gcs_hook.read(query_bucket, query_filepath, 'utf-8')
        for k, v in query_params.items():
            sql = sql.replace(f':{k}', str(v))

        self.bigquery_hook.execute_query_job(
            sql, to_project, to_dataset,
            to_table, to_write_disposition, to_time_partitioning,
            timeout=float(get_config('BIGQUERY_JOB_TIMEOUT', False, 480)))


class PubsubToBigqueryOperator(GoogleBaseEventOperator):

    def __init__(self):
        super().__init__()
        self.bigquery_hook = BigqueryHook()

    def execute(self, data, topic):
        dto = BaseDto.from_dict(data)

        prepared_rows = self.prepare_rows(dto)

        self.bigquery_hook.write(
            project=dto.to_project,
            dataset=dto.to_dataset,
            table=dto.to_table,
            schema=dto.to_schema,
            partition_column=dto.to_partition_column,
            rows=prepared_rows)

    def prepare_row(self, row, event_id, resource, extract_to_cols, keys_format):
        prepared_row = {
            '_event_id': event_id,
            '_resource': resource,
            '_json': json.dumps(row),
            '_created_at': str(datetime.now())
        }

        if extract_to_cols:
            for key in row.keys():
                if (key not in ['_event_id', '_resource', '_json', '_created_at']) and (row[key] is not None):
                    new_key = key
                    if keys_format == 'lowercase':
                        new_key = key.lower()
                        new_key = self.format_key(new_key)
                    elif keys_format == 'snakecase':
                        new_key = self.camel_to_snake(key)
                        new_key = self.format_key(new_key)

                    if isinstance(row[key], list) or isinstance(row[key], dict):
                        prepared_row[new_key] = json.dumps(row[key])
                    else:
                        prepared_row[new_key] = str(row[key])

        return prepared_row

    def prepare_rows(self, dto):
        prepared_rows = dto.data if isinstance(dto.data, list) else [dto.data]
        return [self.prepare_row(row, dto.event_id, dto.resource, dto.to_extract_to_cols, dto.to_keys_format) for row in prepared_rows]

    def camel_to_snake(self, s):
        return ''.join(['_' + c.lower() if c.isupper() else c for c in s]).lstrip('_')

    def format_key(self, key):
        return re.sub(r'[^a-z0-9_]', '', unidecode(key.lower().replace(' ', '_')))


class FileToBigqueryOperator(GoogleBaseEventOperator):

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
