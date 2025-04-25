
import unittest

from datetime import datetime

from airless.core.hook import DatalakeHook


class TestDatalakeHook(unittest.TestCase):

    def setUp(self):
        """Set up an instance of DatalakeHook for testing."""
        self.datalake_hook = DatalakeHook()

    def test_build_metadata(self):
        """Test building metadata"""
        message_id = 1234567890
        origin = 'message-origin'
        
        metadata = self.datalake_hook.build_metadata(message_id, origin)

        assert metadata == {'event_id': message_id, 'resource': origin}

    def test_build_metadata_undefined_data(self):
        """Test building metadata when parameters are not provided"""
        
        metadata = self.datalake_hook.build_metadata(None, None)

        assert metadata == {'event_id': 1234, 'resource': 'local'}

    def test_prepare_row(self):
        """Test method to prepare rows to be inserted to datalake"""
        metadata = {
            'event_id': 1234,
            'resource': 'local'
        }
        row = {
            'foo': 'bar'
        }
        now = datetime(2025, 1, 1, 9, 30, 0)

        actual_output = self.datalake_hook.prepare_row(row, metadata, now)

        expected_output = {
            '_event_id': 1234,
            '_resource': 'local',
            '_json': '{"data": {"foo": "bar"}, "metadata": {"event_id": 1234, "resource": "local"}}',
            '_created_at': '2025-01-01 09:30:00'
        }

        assert actual_output == expected_output


if __name__ == '__main__':
    unittest.main()
