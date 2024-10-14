from deprecation import deprecated


@deprecated(deprecated_in="0.1.2", removed_in="1.0.0",
            details="This class will be deprecated. Please write files directly to datalake instead of stream inserting data to a database")
class BaseDto:
    """Base Data Transfer Object for handling data."""

    def __init__(self, event_id: int, resource: str, to_project: str, to_dataset: str, to_table: str,
                 to_schema: list, to_partition_column: str, to_extract_to_cols: bool,
                 to_keys_format: str, data: dict) -> None:
        """Initializes the BaseDto.

        Args:
            event_id (int): The event ID.
            resource (str): The resource name.
            to_project (str): The target project.
            to_dataset (str): The target dataset.
            to_table (str): The target table.
            to_schema (list): The schema for the data.
            to_partition_column (str): The partition column.
            to_extract_to_cols (bool): Flag to extract columns.
            to_keys_format (str): The format for keys.
            data (dict): The data to be transferred.
        """
        self.event_id = event_id or 1234
        self.resource = resource or 'local'
        self.to_project = to_project
        self.to_dataset = to_dataset
        self.to_table = to_table
        self.to_schema = to_schema
        if to_schema is None:
            self.to_schema = [
                {'key': '_created_at', 'type': 'timestamp', 'mode': 'NULLABLE'},
                {'key': '_json', 'type': 'string', 'mode': 'NULLABLE'},
                {'key': '_event_id', 'type': 'int64', 'mode': 'NULLABLE'},
                {'key': '_resource', 'type': 'string', 'mode': 'NULLABLE'}
            ]

        self.to_partition_column = to_partition_column
        if to_partition_column is None:
            self.to_partition_column = '_created_at'
        self.to_extract_to_cols = to_extract_to_cols
        if to_extract_to_cols is None:
            self.to_extract_to_cols = False
        self.to_keys_format = to_keys_format
        if to_keys_format is None:
            self.to_keys_format = 'nothing'
        self.data = data

    def as_dict(self) -> dict:
        """Converts the DTO to a dictionary.

        Returns:
            dict: The dictionary representation of the DTO.
        """
        return {
            'metadata': {
                'event_id': self.event_id,
                'resource': self.resource,
                'to': {
                    'project': self.to_project,
                    'dataset': self.to_dataset,
                    'table': self.to_table,
                    'schema': self.to_schema,
                    'partition_column': self.to_partition_column,
                    'extract_to_cols': self.to_extract_to_cols,
                    'keys_format': self.to_keys_format
                }
            },
            'data': self.data
        }

    @staticmethod
    def from_dict(d: dict) -> 'BaseDto':
        """Creates a BaseDto from a dictionary.

        Args:
            d (dict): The dictionary to convert.

        Returns:
            BaseDto: The created BaseDto instance.
        """
        to = d.get('metadata', {}).get('to')
        if to:
            project = to.get('project')
            dataset = to['dataset']
            table = to['table']
            schema = to.get('schema')
            partition_column = to.get('partition_column')
            extract_to_cols = to.get('extract_to_cols', False)
            keys_format = to.get('keys_format')
        else:
            project = None
            dataset = d['metadata']['destination_dataset']
            table = d['metadata']['destination_table']
            schema = None
            partition_column = None
            extract_to_cols = d['metadata'].get('extract_to_cols', True)
            keys_format = d['metadata'].get('keys_format')

        return BaseDto(
            event_id=d['metadata'].get('event_id'),
            resource=d['metadata'].get('resource'),
            to_project=project,
            to_dataset=dataset,
            to_table=table,
            to_schema=schema,
            to_partition_column=partition_column,
            to_extract_to_cols=extract_to_cols,
            to_keys_format=keys_format,
            data=d['data']
        )
