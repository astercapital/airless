
import time

from airless.core.operator import BaseEventOperator


class DelayOperator(BaseEventOperator):
    """Introduces a delay in the processing pipeline.

    This operator sleeps for a specified amount of time in seconds.
    The maximum delay is capped at 500 seconds.
    """

    def __init__(self):
        """Initializes the DelayOperator."""
        super().__init__()

    def execute(self, data: dict, topic: str) -> None:
        """Executes the delay operation.

        The function sleeps for the number of seconds specified, capping the maximum wait time at 500 seconds.

        Args:
            data: A dictionary containing a key 'seconds' which determines how many seconds the operator should wait.
            topic: The topic to which the event is associated. This parameter is not utilized in this operator.

        Returns:
            None.
        """

        seconds = data['seconds']
        seconds = max(min(seconds, 500), 0)
        time.sleep(seconds)
