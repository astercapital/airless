
import unittest

from time import time
from unittest.mock import patch

from airless.core.operator import DelayOperator  # Replace with the actual module name where DelayOperator is defined


class TestDelayOperator(unittest.TestCase):

    def setUp(self):
        """Set up for DelayOperator tests."""
        self.operator = DelayOperator()

    @patch('time.sleep', return_value=None)  # Mock sleep to avoid actual delay
    def test_execute_valid_delay(self, mock_sleep):
        """Test executing with a valid delay."""
        data = {'seconds': 10}  # Valid input
        start_time = time()
        self.operator.execute(data, topic='test_topic')
        end_time = time()
        
        # sleep should have been called with 10 seconds
        mock_sleep.assert_called_once_with(10)

        # The execution time should be less than 11 seconds (due to mocking)
        self.assertLess(end_time - start_time, 1)  # Check that we didn't actually sleep

    @patch('time.sleep', return_value=None)  # Mock sleep to avoid actual delay
    def test_execute_with_max_delay(self, mock_sleep):
        """Test executing with a delay that exceeds the maximum."""
        data = {'seconds': 600}  # Exceeds maximum of 500 seconds
        start_time = time()
        self.operator.execute(data, topic='test_topic')
        end_time = time()

        # sleep should have been called with 500 seconds
        mock_sleep.assert_called_once_with(500)

        # The execution time should be less than 1 second (due to mocking)
        self.assertLess(end_time - start_time, 1)

    def test_execute_missing_seconds_key(self):
        """Test executing without the 'seconds' key in data."""
        data = {}  # No seconds key
        with self.assertRaises(KeyError):
            self.operator.execute(data, topic='test_topic')

    @patch('time.sleep', return_value=None)
    def test_execute_with_zero_delay(self, mock_sleep):
        """Test executing with a zero delay."""
        data = {'seconds': 0}  # Zero delay
        start_time = time()
        self.operator.execute(data, topic='test_topic')
        end_time = time()
        
        # sleep should have been called with 0 seconds
        mock_sleep.assert_called_once_with(0)

        # The execution time should be less than 1 second (due to mocking)
        self.assertLess(end_time - start_time, 1)

    @patch('time.sleep', return_value=None)
    def test_execute_with_negative_delay(self, mock_sleep):
        """Test executing with a negative delay."""
        data = {'seconds': -10}  # Negative delay
        start_time = time()
        self.operator.execute(data, topic='test_topic')
        end_time = time()
        
        # sleep should have been called with 0 seconds (since it will not sleep negatively)
        mock_sleep.assert_called_once_with(0)

        # The execution time should be less than 1 second (due to mocking)
        self.assertLess(end_time - start_time, 1)


if __name__ == '__main__':
    unittest.main()
