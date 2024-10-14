
import time

from airless.core.operator import BaseEventOperator


class DelayOperator(BaseEventOperator):

    """Operator that adds a delay to the pipeline.

    This operator introduces a delay in the processing pipeline by sleeping
    for a specified amount of time in seconds. The maximum delay that can
    be set is capped at 500 seconds.

    Attributes:
        None
    """

    def __init__(self):
        """Initializes a DelayOperator instance.

        This method calls the constructor of the parent class 
        `BaseEventOperator`.
        """

        super().__init__()

    def execute(self, data: dict, topic: str) -> None:

        """Executes the delay operation.

        Args:
            data (dict): A dictionary containing a key 'seconds' which
                determines how many seconds the operator should wait.
            topic: The topic to which the event is associated. This parameter
                is not utilized in this operator.

        Raises:
            KeyError: If the 'seconds' key is not present in the data dictionary.

        The function sleeps for the number of seconds specified, capping
        the maximum wait time at 500 seconds.
        """

        seconds = data['seconds']
        seconds = max(min(seconds, 500), 0)
        time.sleep(seconds)
