
from airless.core.operator import BaseFileOperator, BaseEventOperator

from airless.google.cloud.pubsub.hook import GooglePubsubHook


class GoogleBaseFileOperator(BaseFileOperator):
    """Base operator for file operations in Google Cloud."""

    def __init__(self) -> None:
        """Initializes the GoogleBaseFileOperator."""
        super().__init__()
        self.queue_hook = GooglePubsubHook()  # Have to redefine this attribute for each vendor


class GoogleBaseEventOperator(BaseEventOperator):
    """Base operator for event operations in Google Cloud."""

    def __init__(self) -> None:
        """Initializes the GoogleBaseEventOperator."""
        super().__init__()
        self.queue_hook = GooglePubsubHook()  # Have to redefine this attribute for each vendor
