
from airless.operator.base import BaseEventOperator
from airless.hook.notification.slack import SlackHook


class SlackSendOperator(BaseEventOperator):

    def __init__(self):
        super().__init__()
        self.slack_hook = SlackHook()

    def execute(self, data, topic):
        channels = data['channels']
        message = data['message']

        for channel in channels:
            self.slack_hook.send(channel, message)
