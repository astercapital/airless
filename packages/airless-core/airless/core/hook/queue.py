from airless.core.hook import BaseHook


class QueueHook(BaseHook):
    """Hook for interacting with a queue system."""

    def __init__(self) -> None:
        """Initializes the QueueHook."""
        super().__init__()

    def publish(self, project: str, topic: str, data: dict) -> None:
        """Publishes data to a specified topic.

        Args:
            project (str): The project name.
            topic (str): The topic to publish to.
            data (dict): The data to publish.

        Raises:
            NotImplementedError: This method needs to be implemented in a subclass.
        """
        raise NotImplementedError()
