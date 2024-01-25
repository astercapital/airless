
import requests

from airless.hook.base import BaseHook


class SlackHook(BaseHook):

    def __init__(self):
        super().__init__()
        self.api_url = 'slack.com'

    def set_token(self, token):
        self.token = token

    def get_headers(self):
        return {
            'Authorization': f'Bearer {self.token}'
        }

    def send(self, channel, message=None, blocks=None, thread_ts=None, reply_broadcast=False, attachments=None):

        data = {
            'channel': channel,
            'text': message
        }

        if message:
            message = message[:3000]  # slack does not accept long messages
            data['text'] = message

        if blocks:
            data['blocks'] = blocks

        if attachments:
            data['attachments'] = attachments

        if thread_ts:
            data['thread_ts'] = thread_ts
            data['reply_broadcast'] = reply_broadcast

        response = requests.post(
            f'https://{self.api_url}/api/chat.postMessage',
            headers=self.get_headers(),
            json=data,
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    def react(self, channel, reaction, ts):
        data = {
            'channel': channel,
            'name': reaction,
            'timestamp': ts
        }
        response = requests.post(
            f'https://{self.api_url}/api/reactions.add',
            headers=self.get_headers(),
            json=data,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
