from concurrent.futures._base import TimeoutError
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

from airless.core.hook import BaseHook
from airless.core.utils import get_config


class BigqueryHook(BaseHook):
    """Hook for interacting with Google BigQuery.

    This hook provides methods for managing datasets, tables, and jobs in BigQuery.
    It uses the `google-cloud-bigquery` library to communicate with the BigQuery API.
    """

    def __init__(self):
        """Initializes the BigqueryHook.

        Creates a BigQuery client instance.
        """
        super().__init__()
        self.bigquery_client = bigquery.Client()

    def build_table_id(self, project, dataset, table):
        """Builds a BigQuery table ID string.

        Args:
            project (str): The Google Cloud project ID.
            dataset (str): The BigQuery dataset ID.
            table (str): The BigQuery table ID.

        Returns:
            str: The fully qualified table ID in the format 'project.dataset.table'.
        """
        return f'{project or get_config("GCP_PROJECT")}.{dataset}.{table}'

    def list_datasets(self):
        """Lists all datasets in the current project.

        Returns:
            google.cloud.bigquery.dataset.DatasetListItem: An iterator of dataset list items.
        """
        return self.bigquery_client.list_datasets()

    def get_dataset(self, dataset):
        """Gets a BigQuery dataset, creating it if it doesn't exist.

        Args:
            dataset (str): The BigQuery dataset ID.

        Returns:
            google.cloud.bigquery.dataset.Dataset: The BigQuery dataset.
        """
        try:
            bq_dataset = self.bigquery_client.get_dataset(dataset)
        except NotFound:
            bq_dataset = self.bigquery_client.create_dataset(dataset, timeout=30)
            self.logger.debug(f'BQ dataset created {dataset}')
        return bq_dataset

    def get_table(self, project, dataset, table, schema, partition_column):
        """Gets a BigQuery table, creating it if it doesn't exist.

        Args:
            project (str): The Google Cloud project ID.
            dataset (str): The BigQuery dataset ID.
            table (str): The BigQuery table ID.
            schema (list): A list of dictionaries representing the table schema.
                           Each dictionary should have 'key', 'type', and 'mode' keys.
            partition_column (str): The name of the column to use for time-based partitioning.
                                    If None, the table will not be partitioned.

        Returns:
            google.cloud.bigquery.table.Table: The BigQuery table.
        """
        table_id = self.build_table_id(project, dataset, table)
        try:
            bq_table = self.bigquery_client.get_table(table_id)
        except NotFound:
            table = bigquery.Table(
                table_id,
                schema=[
                    bigquery.SchemaField(s['key'], s['type'], mode=s['mode'])
                    for s in schema
                ],
            )
            if partition_column:
                table.time_partitioning = bigquery.TimePartitioning(
                    type_=bigquery.TimePartitioningType.DAY, field=partition_column
                )
            bq_table = self.bigquery_client.create_table(table, timeout=30)
            self.logger.debug(f'BQ table created {project}.{dataset}.{table}')
        return bq_table

    def write(self, project, dataset, table, schema, partition_column, rows):
        """Writes rows to a BigQuery table.

        This method ensures the dataset and table exist, updates the table schema
        if necessary, and then inserts the rows.

        Args:
            project (str): The Google Cloud project ID.
            dataset (str): The BigQuery dataset ID.
            table (str): The BigQuery table ID.
            schema (list): A list of dictionaries representing the table schema.
            partition_column (str): The name of the column for time-based partitioning.
            rows (list): A list of dictionaries representing the rows to insert.

        Raises:
            Exception: If there are errors during the insertion process.
        """
        _ = self.get_dataset(dataset)
        bq_table = self.get_table(project, dataset, table, schema, partition_column)
        bq_table = self.update_table_schema(bq_table, rows)

        errors = self.bigquery_client.insert_rows_json(bq_table, json_rows=rows)

        if errors != []:
            raise Exception(errors)

    def update_table_schema(self, bq_table, rows):
        """Updates the schema of a BigQuery table if new columns are present in the rows.

        Args:
            bq_table (google.cloud.bigquery.table.Table): The BigQuery table object.
            rows (list): A list of dictionaries representing the rows to be inserted.

        Returns:
            google.cloud.bigquery.table.Table: The updated BigQuery table object.
        """
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
        """Gets a unique set of all column names from a list of rows.

        Args:
            rows (list): A list of dictionaries, where each dictionary represents a row.

        Returns:
            set: A set of unique column names.
        """
        return set([key for row in rows for key in list(row.keys())])

    def setup_job_config(
        self,
        from_file_format,
        from_separator,
        from_skip_leading_rows,
        from_quote_character,
        from_encoding,
        to_mode,
        to_schema,
        to_time_partitioning,
    ):
        """Configures a BigQuery load job.

        Args:
            from_file_format (str): The format of the source file (e.g., 'csv', 'json').
            from_separator (str): The delimiter used in CSV files.
            from_skip_leading_rows (int): The number of leading rows to skip in CSV files.
            from_quote_character (str): The character used to quote fields in CSV files.
            from_encoding (str): The encoding of the source file.
            to_mode (str): The write disposition for the load job (e.g., 'overwrite', 'WRITE_APPEND').
            to_schema (list): The schema for the destination table. If None, autodetect is used.
            to_time_partitioning (dict): Configuration for time-based partitioning.
                                       Should include 'type' and 'field'.

        Returns:
            google.cloud.bigquery.job.LoadJobConfig: The configured load job object.

        Raises:
            Exception: If the file format is not supported.
        """
        job_config = bigquery.LoadJobConfig(
            write_disposition='WRITE_TRUNCATE'
            if to_mode == 'overwrite'
            else 'WRITE_APPEND',
            max_bad_records=0,
        )

        if to_schema is None:
            job_config.autodetect = True
        else:
            job_config.schema = to_schema

        if to_time_partitioning:
            job_config.time_partitioning = bigquery.table.TimePartitioning(
                type_=to_time_partitioning['type'], field=to_time_partitioning['field']
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

    def execute_load_job(
        self, from_filepath, to_project, to_dataset, to_table, job_config, timeout=240
    ):
        """Executes a BigQuery load job from a URI.

        Args:
            from_filepath (str): The GCS URI of the source file.
            to_project (str): The Google Cloud project ID for the destination table.
            to_dataset (str): The BigQuery dataset ID for the destination table.
            to_table (str): The BigQuery table ID for the destination table.
            job_config (google.cloud.bigquery.job.LoadJobConfig): The configured load job.
            timeout (int, optional): The timeout for the job in seconds. Defaults to 240.
        """
        table_id = self.build_table_id(to_project, to_dataset, to_table)
        load_job = self.bigquery_client.load_table_from_uri(
            from_filepath, table_id, job_config=job_config, timeout=timeout
        )
        load_job.result()  # Waits for the job to complete.

    def load_file(
        self,
        from_filepath,
        from_file_format,
        from_separator,
        from_skip_leading_rows,
        from_quote_character,
        from_encoding,
        to_project,
        to_dataset,
        to_table,
        to_mode,
        to_schema,
        to_time_partitioning,
    ):
        """Loads data from a file in GCS to a BigQuery table.

        Args:
            from_filepath (str): The GCS URI of the source file.
            from_file_format (str): The format of the source file.
            from_separator (str): The delimiter for CSV files.
            from_skip_leading_rows (int): Number of leading rows to skip for CSV.
            from_quote_character (str): Quote character for CSV files.
            from_encoding (str): File encoding.
            to_project (str): Destination Google Cloud project ID.
            to_dataset (str): Destination BigQuery dataset ID.
            to_table (str): Destination BigQuery table ID.
            to_mode (str): Write disposition (e.g., 'overwrite', 'WRITE_APPEND').
            to_schema (list): Schema for the destination table.
            to_time_partitioning (dict): Configuration for time-based partitioning.
        """
        _ = self.get_dataset(to_dataset)

        job_config = self.setup_job_config(
            from_file_format=from_file_format,
            from_separator=from_separator,
            from_skip_leading_rows=from_skip_leading_rows,
            from_quote_character=from_quote_character,
            from_encoding=from_encoding,
            to_mode=to_mode,
            to_schema=to_schema,
            to_time_partitioning=to_time_partitioning,
        )

        self.execute_load_job(
            from_filepath=from_filepath,
            to_project=to_project,
            to_dataset=to_dataset,
            to_table=to_table,
            job_config=job_config,
        )

        destination_table = self.get_table(
            project=to_project,
            dataset=to_dataset,
            table=to_table,
            schema=to_schema,
            partition_column=(to_time_partitioning or {}).get('field'),
        )
        self.logger.debug(f'Loaded {destination_table.num_rows} rows')

    def execute_query_job(
        self,
        query,
        to_project,
        to_dataset,
        to_table,
        to_write_disposition,
        to_time_partitioning,
        timeout=480,
    ):
        """Executes a BigQuery query job.

        Args:
            query (str): The SQL query to execute.
            to_project (str): The Google Cloud project ID for the destination table (if any).
            to_dataset (str): The BigQuery dataset ID for the destination table (if any).
            to_table (str): The BigQuery table ID for the destination table (if any).
            to_write_disposition (str): The write disposition if writing to a table.
            to_time_partitioning (dict): Configuration for time-based partitioning if writing to a table.
            timeout (int, optional): The timeout for the job in seconds. Defaults to 480.

        Raises:
            TimeoutError: If the job times out.
        """

        job_config = bigquery.QueryJobConfig()

        if (to_dataset is not None) and (to_table is not None):
            job_config.destination = self.build_table_id(
                to_project, to_dataset, to_table
            )

        if to_write_disposition is not None:
            job_config.write_disposition = to_write_disposition

        if to_time_partitioning is not None:
            job_config.time_partitioning = (
                bigquery.table.TimePartitioning().from_api_repr(to_time_partitioning)
            )

        job = self.bigquery_client.query(query, job_config=job_config)
        job.job_id

        try:
            job.result(timeout=timeout, job_retry=None)
        except TimeoutError as e:
            self.bigquery_client.cancel_job(job.job_id)
            raise (e)

    def export_to_gcs(self, from_project, from_dataset, from_table, to_filepath):
        """Exports a BigQuery table to Google Cloud Storage (GCS).

        Args:
            from_project (str): The Google Cloud project ID of the source table.
            from_dataset (str): The BigQuery dataset ID of the source table.
            from_table (str): The BigQuery table ID of the source table.
            to_filepath (str): The GCS URI where the table will be exported.
        """
        job_config = bigquery.ExtractJobConfig()
        job_config.print_header = False

        extract_job = self.bigquery_client.extract_table(
            self.get_table(from_project, from_dataset, from_table, None, None),
            to_filepath,
            job_config=job_config,
            location='US',
        )
        extract_job.result()

    def get_rows_from_table(self, project, dataset, table, timeout=480):
        """Retrieves all rows from a BigQuery table.

        Args:
            project (str): The Google Cloud project ID.
            dataset (str): The BigQuery dataset ID.
            table (str): The BigQuery table ID.
            timeout (int, optional): The timeout for the query in seconds. Defaults to 480.

        Returns:
            google.cloud.bigquery.table.RowIterator: An iterator of rows from the table.
        """
        query = f'SELECT * FROM `{project}.{dataset}.{table}`'
        return self.get_query_results(query, timeout)

    def get_query_results(self, query, timeout=480):
        """Executes a query and returns the results.

        Args:
            query (str): The SQL query to execute.
            timeout (int, optional): The timeout for the query in seconds. Defaults to 480.

        Returns:
            google.cloud.bigquery.table.RowIterator: An iterator of rows resulting from the query.

        Raises:
            TimeoutError: If the query times out.
        """
        job = self.bigquery_client.query(query)
        try:
            return job.result(timeout=timeout, job_retry=None)
        except TimeoutError as e:
            self.bigquery_client.cancel_job(job.job_id)
            raise (e)
