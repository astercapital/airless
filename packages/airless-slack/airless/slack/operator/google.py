
from airless.slack.operator import SlackReactOperator, SlackSendOperator
from airless.google.cloud.secret_manager.hook import GoogleSecretManagerHook
from airless.google.cloud.core.operator import GoogleBaseEventOperator


class GoogleSlackSendOperator(SlackSendOperator, GoogleBaseEventOperator):
    """Slack operator using Google Secret Manager to get secrets."""

    def __init__(self) -> None:
        """Initializes the GoogleSlackSendOperator."""
        super().__init__()
        self.secret_manager_hook = GoogleSecretManagerHook()


class GoogleSlackReactOperator(SlackReactOperator, GoogleBaseEventOperator):
    """Slack operator using Google Secret Manager to get secrets."""

    def __init__(self) -> None:
        """Initializes the GoogleSlackReactOperator."""
        super().__init__()
        self.secret_manager_hook = GoogleSecretManagerHook()
