
from typing import Any, Optional, Union

from airless.core.hook import BaseHook
from airless.core.utils import get_config


class DatalakeHook(BaseHook):

    """DatalakeHook class is designer to write data to the datalake and must be
    implemented by a specific datalake vendor class

    Inherits from:
        BaseHook: The base class for hooks in the airless framework.
    """

    def __init__(self):
        """Initializes the DatalakeHook."""
        super().__init__()

    def send_to_landing_zone(self, data: Any, dataset: str, table: str, message_id: Optional[int], origin: Optional[str], time_partition: bool = False) -> Union[str, None]:
        """Sends data to the landing zone. This method must be implemented by the vendor specific class

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

        raise NotImplementedError('The vendor specific datalake class must implement this method')

    def _validate_non_empty_data(self, data, dataset, table):
        if isinstance(data, list) and (len(data) == 0):
            raise Exception(f'Trying to send empty list to landing zone: {dataset}.{table}')

        if isinstance(data, dict) and (data == {}):
            raise Exception(f'Trying to send empty dict to landing zone: {dataset}.{table}')

    def _dev_send_to_landing_zone(self, data, dataset, table):
        if get_config('ENV') == 'dev':
            self.logger.debug(f'[DEV] Uploading to {dataset}.{table}, Data: {data}')
