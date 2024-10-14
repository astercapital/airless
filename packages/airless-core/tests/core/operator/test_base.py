
import os
import unittest

from cloudevents.http import CloudEvent
from unittest.mock import MagicMock, patch

from airless.core.operator.base import BaseFileOperator, BaseEventOperator, BaseHttpOperator, BaseOperator


class TestBaseOperator(unittest.TestCase):

    def setUp(self):
        self.operator = BaseOperator()
        self.operator.queue_hook = MagicMock()

        os.environ['ENV'] = 'dev'
        os.environ['QUEUE_TOPIC_ERROR'] = 'dev-error'

    def test_extract_message_id(self):
        cloud_event = {'id': '12345'}
        message_id = self.operator.extract_message_id(cloud_event)
        self.assertEqual(message_id, '12345')

    def test_report_error(self):
        self.operator.build_error_message = MagicMock()
        self.operator.report_error('An error occurred', {'key': 'value'})
        self.assertTrue(self.operator.has_error)

        self.operator.build_error_message.assert_called_once()
        self.operator.queue_hook.publish.assert_called_once()

    def test_chain_messages(self):
        messages = [
            {'data': {'content': 'msg1'}, 'topic': 'topic1'},
            {'data': {'content': 'msg2'}, 'topic': 'topic2'},
        ]

        expected_chained_messages = {
            'content': 'msg1',
            'metadata': {
                'run_next': [
                    {
                        'topic': 'topic2',
                        'data': {
                            'content': 'msg2'
                        }
                    }
                ]
            }
        }

        chained_messages, first_topic = self.operator.chain_messages(messages)
        self.assertEqual(chained_messages, expected_chained_messages)
        self.assertEqual(first_topic, 'topic1')


class TestBaseFileOperator(unittest.TestCase):

    def setUp(self):
        self.operator = BaseFileOperator()
        self.operator.queue_hook = MagicMock()

        attributes = {
            'type': 'com.example.sampletype1',
            'source': 'https://example.com/event-producer',
        }
        data = {
            'name': 'test_file.txt'
        }
        self.cloud_event = CloudEvent(attributes, data)
        self.cloud_event['bucket'] = 'test_bucket'

        os.environ['ENV'] = 'dev'
        os.environ['QUEUE_TOPIC_ERROR'] = 'dev-error'

    @patch.object(BaseFileOperator, 'execute', return_value=None)
    def test_run_success(self, mock_execute):
        self.operator.run(self.cloud_event)
        mock_execute.assert_called_once_with('test_bucket', 'test_file.txt')

    @patch.object(BaseFileOperator, 'execute', side_effect=Exception('Error!'))
    def test_run_error(self, mock_execute):
        self.operator.run(self.cloud_event)
        self.assertTrue(self.operator.has_error)


class TestBaseEventOperator(unittest.TestCase):

    def setUp(self):
        self.operator = BaseEventOperator()
        self.operator.queue_hook = MagicMock()

        attributes = {
            'type': 'com.example.sampletype1',
            'source': 'https://example.com/event-producer',
        }
        data = {
            'message': {
                'data': 'eyJrZXkiOiAiVmFsdWUifQ==',
            }
        }
        self.cloud_event = CloudEvent(attributes, data)
        self.cloud_event['source'] = 'path/to/topic-name'

        os.environ['ENV'] = 'dev'
        os.environ['QUEUE_TOPIC_ERROR'] = 'dev-error'

    @patch.object(BaseEventOperator, 'execute', return_value=None)
    def test_run_success(self, mock_execute):
        self.operator.run(self.cloud_event)
        mock_execute.assert_called_once_with({'key': 'Value'}, 'topic-name')

    @patch.object(BaseEventOperator, 'execute', side_effect=Exception("Error!"))
    def test_run_error(self, mock_execute):
        self.operator.run(self.cloud_event)
        self.assertTrue(self.operator.has_error)


class TestBaseHttpOperator(unittest.TestCase):

    def setUp(self):
        self.operator = BaseHttpOperator()
        self.operator.queue_hook = MagicMock()

        os.environ['ENV'] = 'dev'
        os.environ['QUEUE_TOPIC_ERROR'] = 'dev-error'

    @patch.object(BaseHttpOperator, 'execute', return_value=None)
    def test_run_success(self, mock_execute):
        class MockRequest:
            def __init__(self):
                self.base_url = 'http://test.com'
                self.method = 'POST'
                self.form = MagicMock()
                self.args = MagicMock()
                self.data = b'test data'

        request = MockRequest()
        self.operator.run(request)
        mock_execute.assert_called_once_with(request)

    def test_run_error(self):
        class MockRequest:
            def __init__(self):
                self.base_url = 'http://test.com'
                self.method = 'POST'
                self.form = MagicMock()
                self.args = MagicMock()
                self.data = b'test data'

        request = MockRequest()
        with patch.object(self.operator, 'execute', side_effect=Exception("Error!")):
            self.operator.run(request)
            self.assertTrue(self.operator.has_error)


if __name__ == '__main__':
    unittest.main()
