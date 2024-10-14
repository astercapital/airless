
import unittest
from unittest.mock import MagicMock, patch

from airless.core.dto.base import BaseDto
from airless.core.operator import ErrorReprocessOperator


class TestErrorReprocessOperator(unittest.TestCase):
    
    def setUp(self):
        self.operator = ErrorReprocessOperator()
        self.operator.queue_hook = MagicMock()

    def test_execute_successful_retry(self):
        data = {
            'project': 'test_project',
            'input_type': 'event',
            'origin': 'source_topic',
            'event_id': '12345',
            'data': {
                'metadata': {
                    'retry_interval': 2,
                    'retries': 0,
                    'max_retries': 2,
                    'max_interval': 480,
                    'destination': 'error_topic',
                    'dataset': 'test_dataset',
                    'table': 'test_table'
                }
            }
        }
        
        with patch('time.sleep', return_value=None):  # Mocking sleep to avoid delay in tests
            self.operator.execute(data, 'input_topic')
        
        # Check if the event was published to the original topic
        self.operator.queue_hook.publish.assert_called_once_with(
            project='test_project',
            topic='source_topic',
            data={
                'metadata': {
                    'retry_interval': 2,
                    'retries': 1,
                    'max_retries': 2,
                    'max_interval': 480,
                    'destination': 'error_topic',
                    'dataset': 'test_dataset',
                    'table': 'test_table'
                }
            }
        )

    def test_execute_exceed_max_retries(self):
        data = {
            'project': 'test_project',
            'input_type': 'event',
            'origin': 'source_topic',
            'event_id': '12345',
            'data': {
                'metadata': {
                    'retry_interval': 2,
                    'retries': 2,
                    'max_retries': 2,
                    'max_interval': 480,
                    'destination': 'error_topic',
                    'dataset': 'test_dataset',
                    'table': 'test_table'
                }
            }
        }
        
        with patch('time.sleep', return_value=None):
            self.operator.execute(data, 'input_topic')
        
        # Check if the error details were published to the destination topic
        dto = BaseDto(
            event_id='12345',
            resource='source_topic',
            to_project='test_project',
            to_dataset='test_dataset',
            to_table='test_table',
            to_schema=None,
            to_partition_column='_created_at',
            to_extract_to_cols=False,
            to_keys_format=None,
            data=data
        )
        
        self.operator.queue_hook.publish.assert_called_once_with(
            project='test_project',
            topic='error_topic',
            data=dto.as_dict()
        )

    def test_execute_missing_keys(self):
        data = {
            'project': 'test_project',
            'input_type': 'event',
            'origin': 'source_topic',
            'event_id': '12345',
            'data': {
                # Missing 'metadata' key
            }
        }
        
        with self.assertRaises(KeyError):
            self.operator.execute(data, 'input_topic')

    def test_execute_invalid_input_type(self):
        data = {
            'project': 'test_project',
            'input_type': 'invalid_type',
            'origin': 'source_topic',
            'event_id': '12345',
            'data': {
                'metadata': {
                    'retry_interval': 2,
                    'retries': 0,
                    'max_retries': 2,
                    'max_interval': 480,
                    'destination': 'error_topic',
                    'dataset': 'test_dataset',
                    'table': 'test_table'
                }
            }
        }
        
        with patch('time.sleep', return_value=None):
            self.operator.execute(data, 'input_topic')
        
        dto = BaseDto(
            event_id='12345',
            resource='source_topic',
            to_project='test_project',
            to_dataset='test_dataset',
            to_table='test_table',
            to_schema=None,
            to_partition_column='_created_at',
            to_extract_to_cols=False,
            to_keys_format=None,
            data=data
        )
        
        self.operator.queue_hook.publish.assert_called_once_with(
            project='test_project',
            topic='error_topic',
            data=dto.as_dict()
        )


if __name__ == '__main__':
    unittest.main()
