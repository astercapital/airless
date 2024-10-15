import os


def get_config(key: str, raise_exception: bool = True, default_value: str = None) -> str:
    """Retrieves the configuration value for a given key.

    Args:
        key (str): The configuration key to retrieve.
        raise_exception (bool, optional): Whether to raise an exception if the key is not found. Defaults to True.
        default_value (str, optional): The default value to return if the key is not found. Defaults to None.

    Raises:
        Exception: If the key is not found and raise_exception is True.

    Returns:
        str: The configuration value.
    """
    config = os.environ.get(key)
    if config:
        return config
    if raise_exception:
        raise Exception(f'Define the environment variable {key}')
    else:
        return default_value
