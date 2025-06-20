import os
import unittest

from unittest.mock import MagicMock, mock_open, patch


class TestGoogleEmailSendOperatorOperator(unittest.TestCase):
    @patch('airless.core.utils.get_config')
    @patch('builtins.open', new_callable=mock_open)
    @patch('airless.google.cloud.storage.hook.GcsHook')
    @patch('airless.email.hook.GoogleEmailHook')
    @patch(
        'airless.google.cloud.core.operator.GoogleBaseEventOperator.__init__',
        return_value=None,
    )
    def setUp(
        self,
        MockGoogleBaseEventOperatorInit,
        MockGoogleEmailHook,
        MockGcsHook,
        mock_open_file,
        mock_get_config,
    ):
        os.environ['ENV'] = 'dev'
        os.environ['QUEUE_TOPIC_ERROR'] = 'dev-error'
        os.environ['DEFAULT_RECIPIENT_EMAIL_DOMAIN'] = 'domain.com'
        os.environ['SECRET_SMTP'] = 'fake-smtp'

        mock_file_content = '{"user": "test_user", "password": "test_password", "host": "test_host", "port": 587}'
        mock_file_handle = mock_open_file.return_value
        mock_file_handle.read.return_value = mock_file_content

        self.mock_gcs_hook_instance = MockGcsHook.return_value
        self.mock_email_hook_instance = MockGoogleEmailHook.return_value

        from airless.email.operator import GoogleEmailSendOperator

        self.operator = GoogleEmailSendOperator()
        self.operator.queue_hook = MagicMock()
        self.operator.email_hook = MagicMock()
        self.operator.gcs_hook = MagicMock()

        # Verify hooks were instantiated
        MockGoogleEmailHook.assert_called_once()
        MockGcsHook.assert_called_once()
        MockGoogleBaseEventOperatorInit.assert_called_once()

    def test_recipient_string_to_array(self):
        test_data = [
            {'input': 'single', 'expected_output': ['single@domain.com']},
            {
                'input': 'multiple1,multiple2',
                'expected_output': ['multiple1@domain.com', 'multiple2@domain.com'],
            },
            {
                'input': 'complete,foo@bar.com',
                'expected_output': ['complete@domain.com', 'foo@bar.com'],
            },
            {'input': ['single'], 'expected_output': ['single@domain.com']},
            {
                'input': ['multiple1', 'multiple2'],
                'expected_output': ['multiple1@domain.com', 'multiple2@domain.com'],
            },
            {
                'input': ['complete', 'foo@bar.com'],
                'expected_output': ['complete@domain.com', 'foo@bar.com'],
            },
            {
                'input': 'foo,,bar',
                'expected_output': ['foo@domain.com', 'bar@domain.com'],
            },
            {'input': '  user@domain.com  ', 'expected_output': ['user@domain.com']},
            {'input': '', 'expected_output': []},
            {'input': [], 'expected_output': []},
            {
                'input': ['foo', '', 'bar'],
                'expected_output': ['foo@domain.com', 'bar@domain.com'],
            },
        ]

        for td in test_data:
            self.assertEqual(
                self.operator.recipients_string_to_array(td['input']),
                td['expected_output'],
            )
