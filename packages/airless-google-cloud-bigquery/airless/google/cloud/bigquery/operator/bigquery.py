
import json
import re
from typing import Any, Dict, List, Optional

from datetime import datetime
from unidecode import unidecode

from airless.core.utils import get_config
from airless.core.dto import BaseDto

from airless.google.cloud.core.operator import GoogleBaseEventOperator
from airless.google.cloud.bigquery.hook import BigqueryHook
from airless.google.cloud.storage.hook import GcsHook


class GcsQueryToBigqueryOperator(GoogleBaseEventOperator):
    """Operator for executing queries from GCS to BigQuery."""

    def __init__(self) -> None:
        """Initializes the GcsQueryToBigqueryOperator."""
        super().__init__()

        self.gcs_hook = GcsHook()
        self.bigquery_hook = BigqueryHook()

    def execute(self, data: Dict[str, Any], topic: str) -> None:
        """Executes the query from GCS to BigQuery.

        Args:
            data (Dict[str, Any]): The data containing query information.
            topic (str): The Pub/Sub topic.
        """
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

        sql = self.gcs_hook.read_as_string(query_bucket, query_filepath, 'utf-8')
        for k, v in query_params.items():
            sql = sql.replace(f':{k}', str(v))

        self.bigquery_hook.execute_query_job(
            sql, to_project, to_dataset,
            to_table, to_write_disposition, to_time_partitioning,
            timeout=float(get_config('BIGQUERY_JOB_TIMEOUT', False, 480)))


class PubsubToBigqueryOperator(GoogleBaseEventOperator):
    """Operator for transferring messages from Pub/Sub to BigQuery."""

    def __init__(self) -> None:
        """Initializes the PubsubToBigqueryOperator."""
        super().__init__()
        self.bigquery_hook = BigqueryHook()

    def execute(self, data: Dict[str, Any], topic: str) -> None:
        """Executes the transfer from Pub/Sub to BigQuery.

        Args:
            data (Dict[str, Any]): The data containing message information.
            topic (str): The Pub/Sub topic.
        """
        dto = BaseDto.from_dict(data)

        prepared_rows = self.prepare_rows(dto)

        self.bigquery_hook.write(
            project=dto.to_project,
            dataset=dto.to_dataset,
            table=dto.to_table,
            schema=dto.to_schema,
            partition_column=dto.to_partition_column,
            rows=prepared_rows)

    def prepare_row(self, row: Dict[str, Any], event_id: str, resource: str, extract_to_cols: bool, keys_format: Optional[str]) -> Dict[str, Any]:
        """Prepares a single row for BigQuery insertion.

        Args:
            row (Dict[str, Any]): The row data.
            event_id (str): The event ID.
            resource (str): The resource name.
            extract_to_cols (bool): Whether to extract to columns.
            keys_format (Optional[str]): The format for keys.

        Returns:
            Dict[str, Any]: The prepared row.
        """
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

    def prepare_rows(self, dto: BaseDto) -> List[Dict[str, Any]]:
        """Prepares multiple rows for BigQuery insertion.

        Args:
            dto (BaseDto): The data transfer object containing the data.

        Returns:
            List[Dict[str, Any]]: The list of prepared rows.
        """
        prepared_rows = dto.data if isinstance(dto.data, list) else [dto.data]
        return [self.prepare_row(row, dto.event_id, dto.resource, dto.to_extract_to_cols, dto.to_keys_format) for row in prepared_rows]

    def camel_to_snake(self, s: str) -> str:
        """Converts a camelCase string to snake_case.

        Args:
            s (str): The camelCase string.

        Returns:
            str: The converted snake_case string.
        """
        return ''.join(['_' + c.lower() if c.isupper() else c for c in s]).lstrip('_')

    def format_key(self, key: str) -> str:
        """Formats a key by removing invalid characters.

        Args:
            key (str): The key to format.

        Returns:
            str: The formatted key.
        """
        return re.sub(r'[^a-z0-9_]', '', unidecode(key.lower().replace(' ', '_')))
