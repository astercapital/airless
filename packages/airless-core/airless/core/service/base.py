from airless.core import BaseClass


class BaseService(BaseClass):
    """Base class for services in the system."""

    def __init__(self) -> None:
        """Initializes the BaseService."""
        super().__init__()
