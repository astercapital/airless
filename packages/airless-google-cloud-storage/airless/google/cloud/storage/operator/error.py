
from airless.core.operator import ErrorReprocessOperator
from airless.google.cloud.core.operator import GoogleBaseEventOperator
from airless.google.cloud.storage.hook import GcsDatalakeHook


class GoogleErrorReprocessOperator(GoogleBaseEventOperator, ErrorReprocessOperator):
    """Operator for reprocessing errors in Google Cloud."""

    def __init__(self) -> None:
        """Initializes the GoogleErrorReprocessOperator."""
        super().__init__()
        self.datalake_hook = GcsDatalakeHook()
