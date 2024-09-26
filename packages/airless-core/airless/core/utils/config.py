
import os


def get_config(key, raise_exception=True, default_value=None):
    config = os.environ.get(key)
    if config:
        return config
    if raise_exception:
        raise Exception(f'Define the environment variable {key}')
    else:
        return default_value
