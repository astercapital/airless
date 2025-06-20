import os
import unittest

from unittest.mock import MagicMock, mock_open, patch

from airless.email.operator import GoogleEmailSendOperator


class TestGoogleEmailSendOperatorOperator(unittest.TestCase):
    def setUp(self):
        self.operator = GoogleEmailSendOperator()
        self.operator.queue_hook = MagicMock()

        os.environ['ENV'] = 'dev'
        os.environ['QUEUE_TOPIC_ERROR'] = 'dev-error'
        os.environ['DEFAULT_RECIPIENT_EMAIL_DOMAIN'] = 'domain.com'
        os.environ['SECRET_SMTP'] = 'fake-smtp'

    @patch('builtins.open', new_callable=mock_open)
    def test_recipient_string_to_array(self, mock_open_file):
        mock_file_content = '{"user": "test_user", "password": "test_password", "host": "test_host", "port": 587}'

        # Configure the mock_open_file to return our simulated content
        # when its 'read' method is called.
        mock_file_handle = mock_open_file.return_value
        mock_file_handle.read.return_value = mock_file_content

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
