
import os
import unittest

from airless.core.utils import get_config


class ConfigTestCase(unittest.TestCase):

    os.environ['DEFINED_ENV_VAR'] = 'defined-env-var'

    def test_get_config_should_raise_exception(self):
        with self.assertRaises(Exception):
            get_config('UNDEFINED_ENV_VAR')

    def test_get_config_should_return_default_value(self):
        assert get_config('UNDEFINED_ENV_VAR', raise_exception=False) is None
        assert get_config('UNDEFINED_ENV_VAR', raise_exception=False, default_value='test') == 'test'

    def test_get_config_should_return_env_var(self):
        assert get_config('DEFINED_ENV_VAR') == 'defined-env-var'
