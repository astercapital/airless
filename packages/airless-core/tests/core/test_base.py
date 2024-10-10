
import unittest
from unittest.mock import patch
import logging

from airless.core import BaseClass


class TestBaseClass(unittest.TestCase):

    @patch('airless.core.utils.get_config')
    @patch('logging.basicConfig')
    def setUp(self, mock_basic_config, mock_get_config):
        mock_get_config.return_value = 'DEBUG'
        self.instance = BaseClass()
        self.mock_basic_config = mock_basic_config

    def test_logging_level(self):
        logging_level = logging.getLevelName('DEBUG')
        self.mock_basic_config.assert_called_once_with(level=logging_level)

    def test_logger_is_correct(self):
        self.assertIsInstance(self.instance.logger, logging.Logger)
        expected_logger_name = f'{self.instance.__class__.__module__}.{self.instance.__class__.__name__}'
        self.assertEqual(self.instance.logger.name, expected_logger_name)

    def test_instance_creation_debug_log(self):
        with self.assertLogs(self.instance.logger, level='DEBUG') as log:
            self.instance.logger.debug(f'Created class instance {self.instance.__class__.__name__}')
            self.assertIn('DEBUG:airless.core.base.BaseClass:Created class instance BaseClass', log.output)


if __name__ == '__main__':
    unittest.main()
