
from airless.core.operator import RedirectOperator
from airless.google.cloud.core.operator import GoogleBaseEventOperator


class GoogleRedirectOperator(GoogleBaseEventOperator, RedirectOperator):

    """Google Cloud implementation of RedirectOperator.

    Operator that receives one event from a Google Pub/Sub topic and publishes 
    multiple messages to another topic.
    """

    def __init__(self):
        super().__init__()
