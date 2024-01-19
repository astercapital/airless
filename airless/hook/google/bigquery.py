
from concurrent.futures._base import TimeoutError
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

from airless.hook.base import BaseHook


class BigqueryHook(BaseHook):

    def __init__(self):
        super().__init__()
        self.bigquery_client = bigquery.Client()

    def build_table_id(self, project, dataset, table):
        return f'{project}.{dataset}.{table}'

    def list_datasets(self):
        return self.bigquery_client.list_datasets()

    def get_dataset(self, dataset):
        try:
            bq_dataset = self.bigquery_client.get_dataset(dataset)
        except NotFound:
            bq_dataset = self.bigquery_client.create_dataset(dataset, timeout=30)
            self.logger.debug(f'BQ dataset created {dataset}')
        return bq_dataset

    def get_table(self, project, dataset, table, schema, partition_column):
        table_id = self.build_table_id(project, dataset, table)
        try:
            bq_table = self.bigquery_client.get_table(table_id)
        except NotFound:
            table = bigquery.Table(
                table_id,
                schema=[bigquery.SchemaField(s['key'], s['type'], mode=s['mode']) for s in schema]
            )
            if partition_column:
                table.time_partitioning = bigquery.TimePartitioning(
                    type_=bigquery.TimePartitioningType.DAY,
                    field=partition_column
                )
            bq_table = self.bigquery_client.create_table(table, timeout=30)
            self.logger.debug(f'BQ table created {project}.{dataset}.{table}')
        return bq_table

    def write(self, project, dataset, table, schema, partition_column, rows):
        _ = self.get_dataset(dataset)
        bq_table = self.get_table(project, dataset, table, schema, partition_column)
        bq_table = self.update_table_schema(bq_table, rows)

        errors = self.bigquery_client.insert_rows_json(bq_table, json_rows=rows)

        if errors != []:
            raise Exception(errors)

    def update_table_schema(self, bq_table, rows):
        all_columns = self.get_all_columns(rows)
        current_columns = [column.name for column in bq_table.schema]
        update_schema = False
        new_schema = bq_table.schema
        for column in all_columns:
            if column not in current_columns:
                new_schema.append(bigquery.SchemaField(column, 'STRING'))
                update_schema = True

        if update_schema:
            bq_table.schema = new_schema
            bq_table = self.bigquery_client.update_table(bq_table, ['schema'])

        return bq_table

    def get_all_columns(self, rows):
        return set([key for row in rows for key in list(row.keys())])

    def setup_job_config(
            self,
            from_file_format, from_separator, from_skip_leading_rows, from_quote_character, from_encoding,
            to_mode, to_schema, to_time_partitioning):
        job_config = bigquery.LoadJobConfig(
            write_disposition='WRITE_TRUNCATE' if to_mode == 'overwrite' else 'WRITE_APPEND',
            max_bad_records=0)

        if to_schema is None:
            job_config.autodetect = True
        else:
            job_config.schema = to_schema

        if to_time_partitioning:
            job_config.time_partitioning = bigquery.table.TimePartitioning(
                type_=to_time_partitioning['type'],
                field=to_time_partitioning['field']
            )

        if from_file_format == 'csv':
            job_config.source_format = bigquery.SourceFormat.CSV
            job_config.field_delimiter = from_separator
            job_config.allow_quoted_newlines = True
            if from_skip_leading_rows is not None:
                job_config.skip_leading_rows = from_skip_leading_rows
            if from_quote_character is not None:
                job_config.quote_character = from_quote_character
            if from_encoding is not None:
                job_config.encoding = from_encoding

        elif from_file_format == 'json':
            job_config.source_format = bigquery.SourceFormat.NEWLINE_DELIMITED_JSON

        else:
            raise Exception('File format not supported')

        if to_mode == 'WRITE_APPEND':
            job_config.schema_update_options = ['ALLOW_FIELD_ADDITION']

        return job_config

    def execute_load_job(self, from_filepath, to_project, to_dataset, to_table, job_config, timeout=240):
        table_id = self.build_table_id(to_project, to_dataset, to_table)
        load_job = self.bigquery_client.load_table_from_uri(
            from_filepath, table_id,
            job_config=job_config,
            timeout=timeout
        )
        load_job.result()  # Waits for the job to complete.

    def load_file(self,
                  from_filepath, from_file_format, from_separator, from_skip_leading_rows,
                  from_quote_character, from_encoding,
                  to_project, to_dataset, to_table, to_mode, to_schema, to_time_partitioning):
        _ = self.get_dataset(to_dataset)

        job_config = self.setup_job_config(
            from_file_format=from_file_format,
            from_separator=from_separator,
            from_skip_leading_rows=from_skip_leading_rows,
            from_quote_character=from_quote_character,
            from_encoding=from_encoding,
            to_mode=to_mode,
            to_schema=to_schema,
            to_time_partitioning=to_time_partitioning)

        self.execute_load_job(
            from_filepath=from_filepath,
            to_project=to_project,
            to_dataset=to_dataset,
            to_table=to_table,
            job_config=job_config)

        destination_table = self.get_table(
            project=to_project,
            dataset=to_dataset,
            table=to_table,
            schema=to_schema,
            partition_column=(to_time_partitioning or {}).get('field'))
        self.logger.debug(f'Loaded {destination_table.num_rows} rows')

    def execute_query_job(
            self, query, to_project, to_dataset, to_table, to_write_disposition, to_time_partitioning, timeout=480):

        job_config = bigquery.QueryJobConfig()

        if (to_dataset is not None) and (to_table is not None):
            job_config.destination = self.build_table_id(to_project, to_dataset, to_table)

        if to_write_disposition is not None:
            job_config.write_disposition = to_write_disposition

        if to_time_partitioning is not None:
            job_config.time_partitioning = \
                bigquery.table.TimePartitioning().from_api_repr(to_time_partitioning)

        job = self.bigquery_client.query(query, job_config=job_config)
        job.job_id

        try:
            job.result(timeout=timeout, job_retry=None)
        except TimeoutError as e:
            self.bigquery_client.cancel_job(job.job_id)
            raise(e)

    def export_to_gcs(self, from_project, from_dataset, from_table, to_filepath):
        job_config = bigquery.ExtractJobConfig()
        job_config.print_header = False

        extract_job = self.bigquery_client.extract_table(
            self.get_table(from_project, from_dataset, from_table, None, None),
            to_filepath,
            job_config=job_config,
            location='US'
        )
        extract_job.result()

    def get_rows_from_table(self, project, dataset, table, timeout=480):
        query = f'SELECT * FROM `{project}.{dataset}.{table}`'
        return self.get_query_results(query, timeout)

    def get_query_results(self, query, timeout=480):
        job = self.bigquery_client.query(query)
        try:
            return job.result(timeout=timeout, job_retry=None)
        except TimeoutError as e:
            self.bigquery_client.cancel_job(job.job_id)
            raise(e)
