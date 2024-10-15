
from airless.core.operator import DelayOperator
from airless.google.cloud.core.operator import GoogleBaseEventOperator


class GoogleDelayOperator(GoogleBaseEventOperator, DelayOperator):
    """Operator that adds a delay to the pipeline."""

    def __init__(self) -> None:
        """Initializes the GoogleDelayOperator."""
        super().__init__()
