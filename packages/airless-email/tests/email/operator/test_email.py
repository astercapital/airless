import os
import unittest

from unittest.mock import MagicMock

from airless.email.operator import GoogleEmailSendOperator


class TestGoogleEmailSendOperatorOperator(unittest.TestCase):
    def setUp(self):
        self.operator = GoogleEmailSendOperator()
        self.operator.queue_hook = MagicMock()

        os.environ['ENV'] = 'dev'
        os.environ['QUEUE_TOPIC_ERROR'] = 'dev-error'
        os.environ['DEFAULT_RECIPIENT_EMAIL_DOMAIN'] = 'domain.com'

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
        ]

        for td in test_data:
            self.assertEqual(
                self.operator.recipients_string_to_array(td['input']),
                td['expected_output'],
            )
