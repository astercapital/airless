
import json

from datetime import datetime

from airless.config import get_config
from airless.dto.pubsub_to_bq import PubsubToBqDto
from airless.hook.google.bigquery import BigqueryHook
from airless.hook.google.storage import GcsHook
from airless.operator.base import BaseEventOperator


class GcsQueryToBigqueryOperator(BaseEventOperator):

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
            to_table, to_write_disposition, to_time_partitioning)


class PubsubToBqOperator(BaseEventOperator):

    def __init__(self):
        super().__init__()
        self.bigquery_hook = BigqueryHook()

    def execute(self, data, topic):
        dto = PubsubToBqDto.from_dict(data)

        prepared_rows = self.prepare_rows(dto)

        self.bigquery_hook.write(
            project=dto.to_project,
            dataset=dto.to_dataset,
            table=dto.to_table,
            schema=dto.to_schema,
            partition_column=dto.to_partition_column,
            rows=prepared_rows)

    def prepare_row(self, row, event_id, resource):
        return {
            '_event_id': event_id,
            '_resource': resource,
            '_json': json.dumps(row),
            '_created_at': str(datetime.now())
        }

    def prepare_rows(self, dto):
        prepared_rows = dto.data if isinstance(dto.data, list) else [dto.data]
        return [self.prepare_row(row, dto.event_id, dto.resource) for row in prepared_rows]
