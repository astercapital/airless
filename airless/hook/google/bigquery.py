
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

from airless.hook.base import BaseHook


class BigqueryHook(BaseHook):

    def __init__(self):
        super().__init__()
        self.bigquery_client = bigquery.Client()

    def build_table_id(self, project, dataset, table):
        return f'{project}.{dataset}.{table}'

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

    def setup_job_config(self, mode, file_format, separator, schema, skip_leading_rows, quote_character, encoding, time_partitioning):
        job_config = bigquery.LoadJobConfig(
            write_disposition='WRITE_TRUNCATE' if mode == 'overwrite' else 'WRITE_APPEND',
            max_bad_records=0)

        if schema is None:
            job_config.autodetect = True
        else:
            job_config.schema = schema

        if time_partitioning:
            job_config.time_partitioning = bigquery.table.TimePartitioning(
                type_=time_partitioning['type'],
                field=time_partitioning['field']
            )

        if file_format == 'csv':
            job_config.source_format = bigquery.SourceFormat.CSV
            job_config.field_delimiter = separator
            job_config.allow_quoted_newlines = True
            if skip_leading_rows is not None:
                job_config.skip_leading_rows = skip_leading_rows
            if quote_character is not None:
                job_config.quote_character = quote_character
            if encoding is not None:
                job_config.encoding = encoding

        elif file_format == 'json':
            job_config.source_format = bigquery.SourceFormat.NEWLINE_DELIMITED_JSON

        else:
            raise Exception('File format not supported')

        if mode == 'WRITE_APPEND':
            job_config.schema_update_options = ['ALLOW_FIELD_ADDITION']

        return job_config

    def execute_load_job(self, from_filepath, project, dataset, table, job_config):
        table_id = self.build_table_id(project, dataset, table)
        load_job = self.bigquery_client.load_table_from_uri(
            from_filepath, table_id,
            job_config=job_config,
            timeout=240
        )
        load_job.result()  # Waits for the job to complete.

    def load_file_to_bq(self, file_uri, dataset, table, mode, file_format, separator, schema, skip_leading_rows, quote_character, encoding, time_partitioning):
        _ = self.get_dataset(dataset)

        job_config = self.setup_job_config(mode, file_format, separator, schema, skip_leading_rows, quote_character, encoding, time_partitioning)

        self.execute_load_job(dataset, table, file_uri, job_config)

        destination_table = self.get_table(dataset, table)
        self.logger.debug(f'Loaded {destination_table.num_rows} rows')

    def execute_query_job(
            self, query, to_project, to_dataset, to_table, to_write_disposition, to_time_partitioning):

        job_config = bigquery.QueryJobConfig()

        if (to_dataset is not None) and (to_table is not None):
            job_config.destination = self.build_table_id(to_project, to_dataset, to_table)

        if to_write_disposition is not None:
            job_config.write_disposition = to_write_disposition

        if to_time_partitioning is not None:
            job_config.time_partitioning = \
                bigquery.table.TimePartitioning().from_api_repr(to_time_partitioning)

        job = self.bigquery_client.query(query, job_config=job_config)
        job.result()

    def export_to_gcs(self, to_filepath, dataset, table, bucket, directory, filename):
        job_config = bigquery.ExtractJobConfig()
        job_config.print_header = False

        extract_job = self.bigquery_client.extract_table(
            self.get_table(dataset, table),
            to_filepath,
            job_config=job_config,
            location='US'
        )
        extract_job.result()

    def get_rows_from_table(self, dataset, table):
        query = f'SELECT * FROM {dataset}.{table}'
        job = self.bigquery_client.query(query)
        return job.result()

    def get_query_results(self, query):
        job = self.bigquery_client.query(query)
        return job.result()
