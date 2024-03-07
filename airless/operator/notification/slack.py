
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
        channels = data.get('channels', [])
        secret_id = data.get('secret_id', 'slack_alert')
        message = data.get('message')
        blocks = data.get('blocks')
        attachments = data.get('attachments')
        thread_ts = data.get('thread_ts')
        reply_broadcast = data.get('reply_broadcast', False)
        response_url = data.get('response_url')
        response_type = data.get('response_type')
        replace_original = data.get('replace_original')

        token = self.secret_manager_hook.get_secret(get_config('GCP_PROJECT'), secret_id, True)['bot_token']
        self.slack_hook.set_token(token)

        if not channels and not response_url:
            raise Exception('Either channels or response_url must be set')

        for channel in channels:
            response = self.slack_hook.send(
                channel=channel,
                message=message,
                blocks=blocks,
                thread_ts=thread_ts,
                reply_broadcast=reply_broadcast,
                attachments=attachments,
                response_type=response_type,
                replace_original=replace_original)
            self.logger.debug(response)

        if response_url:
            response = self.slack_hook.send(
                message=message,
                blocks=blocks,
                thread_ts=thread_ts,
                reply_broadcast=reply_broadcast,
                attachments=attachments,
                response_url=response_url,
                response_type=response_type,
                replace_original=replace_original)
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
