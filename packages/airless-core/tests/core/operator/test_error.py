
import os
import unittest
from unittest.mock import MagicMock, patch

from airless.core.operator import ErrorReprocessOperator


class TestErrorReprocessOperator(unittest.TestCase):
    
    def setUp(self):
        self.operator = ErrorReprocessOperator()
        self.operator.queue_hook = MagicMock()
        self.operator.datalake_hook = MagicMock()

    @patch('time.sleep', return_value=None)  # Mock sleep to avoid actual delay
    @patch('airless.core.operator.ErrorReprocessOperator._notify_email', return_value=None)
    @patch('airless.core.operator.ErrorReprocessOperator._notify_slack', return_value=None)
    def test_execute_successful_retry(self, notify_slack, notify_email, mock_sleep):
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
                    'dataset': 'error_dataset',
                    'table': 'error_table'
                }
            }
        }

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
                    'dataset': 'error_dataset',
                    'table': 'error_table'
                }
            }
        )

        notify_slack.assert_not_called()
        notify_email.assert_not_called()

    @patch('time.sleep', return_value=None)  # Mock sleep to avoid actual delay
    @patch('airless.core.operator.ErrorReprocessOperator._notify_email', return_value=None)
    @patch('airless.core.operator.ErrorReprocessOperator._notify_slack', return_value=None)
    def test_execute_exceed_max_retries(self, notify_slack, notify_email, mock_sleep):
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
                    'dataset': 'error_dataset',
                    'table': 'error_table'
                }
            }
        }
        
        self.operator.execute(data, 'input_topic')
        
        self.operator.datalake_hook.send_to_landing_zone.assert_called_once_with(
            data=data,
            dataset='error_dataset',
            table='error_table',
            message_id='12345',
            origin='source_topic',
            time_partition=True
        )

        notify_slack.assert_called_once_with(
            origin='source_topic',
            message_id='12345',
            data=data
        )

        notify_email.assert_called_once_with(
            origin='source_topic',
            message_id='12345',
            data=data
        )

    @patch('time.sleep', return_value=None)  # Mock sleep to avoid actual delay
    @patch('airless.core.operator.ErrorReprocessOperator._notify_email', return_value=None)
    @patch('airless.core.operator.ErrorReprocessOperator._notify_slack', return_value=None)
    def test_execute_exceed_max_retries_without_error_destination(self, notify_slack, notify_email, mock_sleep):
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
                    'max_interval': 480
                }
            }
        }
        env_vars = {
            'ERROR_DATASET': 'env_error_dataset',
            'ERROR_TABLE': 'env_error_table'
        }
        
        with patch.dict(os.environ, env_vars):
            self.operator.execute(data, 'input_topic')

        self.operator.datalake_hook.send_to_landing_zone.assert_called_once_with(
            data=data,
            dataset='env_error_dataset',
            table='env_error_table',
            message_id='12345',
            origin='source_topic',
            time_partition=True
        )

        notify_slack.assert_called_once_with(
            origin='source_topic',
            message_id='12345',
            data=data
        )

        notify_email.assert_called_once_with(
            origin='source_topic',
            message_id='12345',
            data=data
        )

    def test_execute_missing_input_type(self):
        data = {
            'project': 'test_project',
            # 'input_type': 'event',
            'origin': 'source_topic',
            'event_id': '12345',
            'data': {}
        }

        with self.assertRaises(KeyError):
            self.operator.execute(data, 'error_topic')

    def test_execute_missing_data(self):
        data = {
            'project': 'test_project',
            'input_type': 'event',
            'origin': 'source_topic',
            'event_id': '12345',
            # 'data': {}
        }

        with self.assertRaises(KeyError):
            self.operator.execute(data, 'error_topic')

    @patch('time.sleep', return_value=None)  # Mock sleep to avoid actual delay
    @patch('airless.core.operator.ErrorReprocessOperator._notify_email', return_value=None)
    @patch('airless.core.operator.ErrorReprocessOperator._notify_slack', return_value=None)
    def test_execute_file_input_type(self, notify_slack, notify_email, mock_sleep):
        data = {
            'project': 'test_project',
            'input_type': 'file',
            'origin': 'source_topic',
            'event_id': '12345',
            'data': {
                'metadata': {
                    'retry_interval': 2,
                    'retries': 0,
                    'max_retries': 2,
                    'max_interval': 480,
                    'dataset': 'error_dataset',
                    'table': 'error_table'
                }
            }
        }
        
        self.operator.execute(data, 'input_topic')

        self.operator.datalake_hook.send_to_landing_zone.assert_called_once_with(
            data=data,
            dataset='error_dataset',
            table='error_table',
            message_id='12345',
            origin='source_topic',
            time_partition=True
        )

        notify_slack.assert_called_once_with(
            origin='source_topic',
            message_id='12345',
            data=data
        )

        notify_email.assert_called_once_with(
            origin='source_topic',
            message_id='12345',
            data=data
        )

    def test_notify_email_queue_topic_not_set(self):
        origin = 'origin-topic'
        message_id = '12345'
        data = {
            'input_type': 'input-type',
            'data': {
                'foo': 'bar'
            },
            'error': 'error msg'
        }
        with patch.dict(os.environ, {}):
            self.operator._notify_email(origin, message_id, data)

        self.operator.queue_hook.publish.assert_not_called()

    def test_notify_email(self):
        origin = 'origin-topic'
        message_id = '12345'
        data = {
            'input_type': 'input-type',
            'data': {
                'foo': 'bar'
            },
            'error': 'error msg'
        }
        env_vars = {
            'QUEUE_TOPIC_EMAIL_SEND': 'queue-topic-email-send',
            'EMAIL_SENDER_ERROR': 'foo@bar.com',
            'EMAIL_RECIPIENTS_ERROR': '["rec1@test.com", "rec2@test.com"]',
            'EMAIL_OPERATOR_PROJECT': 'email-operator-project'
        }

        with patch.dict(os.environ, env_vars):
            self.operator._notify_email(origin, message_id, data)

        email_message = {
            'sender': 'foo@bar.com',
            'recipients': ['rec1@test.com', 'rec2@test.com'],
            'subject': 'origin-topic | 12345',
            'content': 'Input Type: input-type Origin: origin-topic\nMessage ID: 12345\n\n {"foo": "bar"}\n\nerror msg'
        }

        self.operator.queue_hook.publish.assert_called_once_with(
            project='email-operator-project',
            topic='queue-topic-email-send',
            data=email_message)

    def test_notify_email_to_same_topic(self):
        origin = 'origin-topic'
        message_id = '12345'
        data = {
            'input_type': 'input-type',
            'data': {
                'foo': 'bar'
            },
            'error': 'error msg'
        }
        env_vars = {
            'QUEUE_TOPIC_EMAIL_SEND': origin,
            'EMAIL_SENDER_ERROR': 'foo@bar.com',
            'EMAIL_RECIPIENTS_ERROR': '["rec1@test.com", "rec2@test.com"]',
            'EMAIL_OPERATOR_PROJECT': 'email-operator-project'
        }

        with patch.dict(os.environ, env_vars):
            self.operator._notify_email(origin, message_id, data)

        self.operator.queue_hook.publish.assert_not_called()

    def test_notify_slack_queue_topic_not_set(self):
        origin = 'origin-topic'
        message_id = '12345'
        data = {}
        self.operator._notify_slack(origin, message_id, data)

        self.operator.queue_hook.publish.assert_not_called()

    def test_notify_slack(self):
        origin = 'origin-topic'
        message_id = '12345'
        data = {
            'input_type': 'input-type',
            'data': {
                'foo': 'bar'
            },
            'error': 'error msg'
        }
        env_vars = {
            'QUEUE_TOPIC_SLACK_SEND': 'queue-topic-slack-send',
            'SLACK_CHANNELS_ERROR': '["channel1", "channel2"]',
            'SLACK_OPERATOR_PROJECT': 'slack-operator-project'
        }

        with patch.dict(os.environ, env_vars):
            self.operator._notify_slack(origin, message_id, data)

        slack_message = {
            'channels': ['channel1', 'channel2'],
            'message': 'origin-topic | 12345\n\n{"foo": "bar"}\n\nerror msg'
        }

        self.operator.queue_hook.publish.assert_called_once_with(
            project='slack-operator-project',
            topic='queue-topic-slack-send',
            data=slack_message)

    def test_notify_slack_to_same_topic(self):
        origin = 'origin-topic'
        message_id = '12345'
        data = {
            'input_type': 'input-type',
            'data': {
                'foo': 'bar'
            },
            'error': 'error msg'
        }
        env_vars = {
            'QUEUE_TOPIC_SLACK_SEND': origin,
            'SLACK_CHANNELS_ERROR': '["channel1", "channel2"]',
            'SLACK_OPERATOR_PROJECT': 'slack-operator-project'
        }

        with patch.dict(os.environ, env_vars):
            self.operator._notify_slack(origin, message_id, data)

        self.operator.queue_hook.publish.assert_not_called()


if __name__ == '__main__':
    unittest.main()
