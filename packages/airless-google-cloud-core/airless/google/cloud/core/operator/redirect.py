
from airless.core.operator import RedirectOperator
from airless.google.cloud.core.operator import GoogleBaseEventOperator


class GoogleRedirectOperator(GoogleBaseEventOperator, RedirectOperator):

    """
    Operator that receives one event from a pubsub topic
    and publish multiple messages to another topic.

    It can receive 4 parameters:
    project: the project where the destination pubsub is hosted
    topic: the pubsub topic it must publish the newly generated messages
    messages: a list of messages to publish the topic
    params: a list of dicts containing a key and a list of values

    The output messages will be the product of messages and every param values list
    """

    def __init__(self):
        super().__init__()
