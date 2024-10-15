import logging

from airless.core.utils import get_config


class BaseClass:
    """Base class for all components with logging capabilities."""

    def __init__(self) -> None:
        """Initializes the BaseClass and sets up logging."""
        self.logger = logging.getLogger(f'{self.__class__.__module__}.{self.__class__.__name__}')
        logging.basicConfig(level=logging.getLevelName(get_config('LOG_LEVEL')))
        self.logger.debug(f'Created class instance {self.__class__.__name__}')
