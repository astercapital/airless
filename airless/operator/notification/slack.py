
from airless.config import get_config
from airless.operator.base import BaseEventOperator
from airless.hook.google.secret_manager import SecretManagerHook
from airless.hook.notification.slack import SlackHook


class SlackSendOperator(BaseEventOperator):

    def __init__(self):
        super().__init__()
        self.slack_hook = SlackHook()
        self.secret_manager_hook = SecretManagerHook()

    def execute(self, data, topic):
        channels = data['channels']
        secret_id = data.get('secret_id', 'slack_alert')
        message = data.get('message')
        blocks = data.get('blocks')
        attachments = data.get('attachments')
        thread_ts = data.get('thread_ts')
        reply_broadcast = data.get('reply_broadcast', False)

        token = self.secret_manager_hook.get_secret(get_config('GCP_PROJECT'), secret_id, True)['bot_token']
        self.slack_hook.set_token(token)

        for channel in channels:
            response = self.slack_hook.send(channel, message, blocks, thread_ts, reply_broadcast, attachments)
            self.logger.debug(response)


class SlackReactOperator(BaseEventOperator):

    def __init__(self):
        super().__init__()
        self.slack_hook = SlackHook()
        self.secret_manager_hook = SecretManagerHook()

    def execute(self, data, topic):
        channel = data['channel']
        secret_id = data.get('secret_id', 'slack_alert')
        reaction = data.get('reaction')
        ts = data.get('ts')

        token = self.secret_manager_hook.get_secret(get_config('GCP_PROJECT'), secret_id, True)['bot_token']
        self.slack_hook.set_token(token)

        response = self.slack_hook.react(channel, reaction, ts)
        self.logger.debug(response)
