
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

    def send(self, channel, message=None, blocks=None):

        data = {
            'channel': channel,
            'text': message
        }

        if message:
            message = message[:3000]  # slack does not accept long messages
            data['text'] = message

        if blocks:
            data['blocks'] = blocks

        response = requests.post(
            f'https://{self.api_url}/api/chat.postMessage',
            headers=self.get_headers(),
            json=data,
            timeout=10
        )
        response.raise_for_status()
