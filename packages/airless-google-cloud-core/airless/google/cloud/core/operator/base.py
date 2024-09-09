
from airless.core.operator.base import BaseFileOperator, BaseEventOperator

from airless.google.cloud.pubsub.hook import GooglePubsubHook


class BaseGoogleFileOperator(BaseFileOperator):

    def __init__(self):
        super().__init__()
        self.queue_hook = GooglePubsubHook()  # Have to redefine this attribute for each vendor


class BaseGoogleEventOperator(BaseEventOperator):

    def __init__(self):
        super().__init__()
        self.queue_hook = GooglePubsubHook()  # Have to redefine this attribute for each vendor
