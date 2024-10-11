
import unittest
from unittest.mock import MagicMock, patch
from airless.core.operator import RedirectOperator


class TestRedirectOperator(unittest.TestCase):

    @patch('airless.core.utils.get_config')
    def setUp(self, mock_get_config):
        mock_get_config.return_value = 'mock_project'
        self.operator = RedirectOperator()
        self.operator.queue_hook = MagicMock()

    def test_execute_without_messages_or_params(self):
        data = {
            'project': 'test_project',
            'topic': 'test_topic',
        }
        
        self.operator.execute(data, 'test_topic')
        
        self.operator.queue_hook.publish.assert_called_once_with(
            'test_project', 'test_topic', {})

    def test_execute_with_messages(self):
        data = {
            'project': 'test_project',
            'topic': 'test_topic',
            'messages': [{'key1': 'value1'}, {'key2': 'value2'}],
            'params': [],
        }
        
        self.operator.execute(data, 'test_topic')

        self.operator.queue_hook.publish.assert_any_call(
            'test_project', 
            'test_topic', 
            {'key1': 'value1'}
        )

        self.operator.queue_hook.publish.assert_any_call(
            'test_project', 
            'test_topic', 
            {'key2': 'value2'}
        )
        
    def test_execute_with_params(self):
        data = {
            'project': 'test_project',
            'topic': 'test_topic',
            'messages': [{'key1': 'value1'}],
            'params': [{'key': 'key2.nested', 'values': ['new_value1', 'new_value2']}],
        }
        
        self.operator.execute(data, 'test_topic')
        
        self.operator.queue_hook.publish.assert_any_call(
            'test_project', 
            'test_topic', 
            {'key1': 'value1', 'key2': {'nested': 'new_value1'}}
        )
        
        self.operator.queue_hook.publish.assert_any_call(
            'test_project', 
            'test_topic', 
            {'key1': 'value1', 'key2': {'nested': 'new_value2'}}
        )

    def test_add_key(self):
        message = {'key1': 'value1'}
        keys = ['key2', 'nested']
        value = 'new_value'
        
        result = self.operator.add_key(message, keys, value)
        
        expected = {'key1': 'value1', 'key2': {'nested': 'new_value'}}
        self.assertEqual(result, expected)

    def test_add_param_to_message(self):
        message = {'key1': 'value1'}
        param = {'key': 'key2.nested', 'values': ['value1', 'value2']}

        result = self.operator.add_param_to_message(message, param)

        expected = [
            {'key1': 'value1', 'key2': {'nested': 'value1'}},
            {'key1': 'value1', 'key2': {'nested': 'value2'}},
        ]
        self.assertEqual(result, expected)

    def test_param_to_messages(self):
        messages = [{'key1': 'value1'}, {'key2': 'value2'}]
        param = {'key': 'key3.nested', 'values': ['value1', 'value2']}

        result = self.operator.add_param_to_messages(messages, param)

        expected = [
            {'key1': 'value1', 'key3': {'nested': 'value1'}},
            {'key1': 'value1', 'key3': {'nested': 'value2'}},
            {'key2': 'value2', 'key3': {'nested': 'value1'}},
            {'key2': 'value2', 'key3': {'nested': 'value2'}},
        ]
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
