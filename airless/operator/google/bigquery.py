
from airless.config import get_config
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
        query_bucket = query['bucket']
        query_filepath = query['filepath']
        query_params = query.get('params', {})

        to = data.get('to', {})

        to_project = to.get('project', get_config('GCP_PROJECT'))
        to_dataset = to.get('dataset')
        to_table = to.get('table')
        to_write_disposition = to.get('write_disposition')
        to_time_partitioning = to.get('time_partitioning')

        sql = self.gcs_hook.read(query_bucket, query_filepath, 'utf-8')
        for k, v in query_params.items():
            sql = sql.replace(f':{k}', str(v))

        self.bigquery_hook.execute_query_job(
            sql, to_project, to_dataset,
            to_table, to_write_disposition, to_time_partitioning)
