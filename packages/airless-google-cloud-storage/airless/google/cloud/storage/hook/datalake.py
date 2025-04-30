
import pyarrow as pa

from typing import Any, Optional, Union

from airless.core.utils import get_config
from airless.core.hook import DatalakeHook

from airless.google.cloud.storage.hook import GcsHook


class GcsDatalakeHook(GcsHook, DatalakeHook):
    """Hook for interacting with GCS Datalake."""

    def __init__(self) -> None:
        """Initializes the GcsDatalakeHook."""
        super().__init__()

    def send_to_landing_zone(self, data: Any, dataset: str, table: str, message_id: Optional[int], origin: Optional[str], time_partition: bool = False) -> Union[str, None]:
        """Sends data to the landing zone in GCS.

        Args:
            data (Any): The data to send.
            dataset (str): The dataset name.
            table (str): The table name.
            message_id (Optional[int]): The message ID.
            origin (Optional[str]): The origin of the data.
            time_partition (bool, optional): Whether to use time partitioning. Defaults to False.

        Returns:
            Union[str, None]: The path to the uploaded file or None.
        """

        self._validate_non_empty_data(data, dataset, table)
        self._dev_send_to_landing_zone(data, dataset, table)

        if get_config('ENV') == 'prod':
            metadata = self.build_metadata(message_id, origin)
            prepared_rows, now = self.prepare_rows(data, metadata)

            if time_partition:
                time_partition_name = 'date'
                schema = pa.schema([
                    ('_event_id', pa.int64()),
                    ('_resource', pa.string()),
                    ('_json', pa.string()),
                    ('_created_at', pa.timestamp('us'))
                ])
                return self.upload_parquet_from_memory(
                    data=prepared_rows,
                    bucket=get_config('GCS_BUCKET_LANDING_ZONE'),
                    directory=f'{dataset}/{table}/{time_partition_name}={now.strftime("%Y-%m-%d")}',
                    filename='tmp.parquet',
                    add_timestamp=True,
                    schema=schema)
            else:
                return self.upload_from_memory(
                    data=prepared_rows,
                    bucket=get_config('GCS_BUCKET_LANDING_ZONE'),
                    directory=f'{dataset}/{table}',
                    filename='tmp.json',
                    add_timestamp=True)
