
from airless.config import get_config


class PubsubToBqDto():

    def __init__(self, event_id, resource, to_project, to_dataset, to_table, to_schema, to_partition_column,
                 to_extract_to_cols, to_keys_format, data):
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

    def as_dict(self):
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

    def from_dict(d):
        to = d.get('metadata', {}).get('to')
        if to:
            project = to.get('project', get_config('GCP_PROJECT'))
            dataset = to['dataset']
            table = to['table']
            schema = to.get('schema')
            partition_column = to.get('partition_column')
            extract_to_cols = to.get('extract_to_cols', False)
            keys_format = to.get('keys_format')
        else:
            project = get_config('GCP_PROJECT')
            dataset = d['metadata']['destination_dataset']
            table = d['metadata']['destination_table']
            schema = None
            partition_column = None
            extract_to_cols = d['metadata'].get('extract_to_cols', True)
            keys_format = d['metadata'].get('keys_format')

        return PubsubToBqDto(
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
