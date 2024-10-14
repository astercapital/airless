from airless.core import BaseClass


class BaseHook(BaseClass):
    """Base class for hooks in the system."""

    def __init__(self) -> None:
        """Initializes the BaseHook."""
        super().__init__()
