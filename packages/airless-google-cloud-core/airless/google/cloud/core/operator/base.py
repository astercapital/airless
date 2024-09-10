
from airless.core.operator import BaseFileOperator, BaseEventOperator

from airless.google.cloud.pubsub.hook import GooglePubsubHook


class GoogleBaseFileOperator(BaseFileOperator):

    def __init__(self):
        super().__init__()
        self.queue_hook = GooglePubsubHook()  # Have to redefine this attribute for each vendor


class GoogleBaseEventOperator(BaseEventOperator):

    def __init__(self):
        super().__init__()
        self.queue_hook = GooglePubsubHook()  # Have to redefine this attribute for each vendor
