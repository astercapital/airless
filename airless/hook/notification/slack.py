
import requests

from airless.config import get_config
from airless.hook.base import BaseHook
from airless.hook.google.secret_manager import SecretManagerHook


class SlackHook(BaseHook):

    def __init__(self):
        super().__init__()
        secret_manager_hook = SecretManagerHook()
        self.token = secret_manager_hook.get_secret(get_config('GCP_PROJECT'), 'slack_alert', True)['bot_token']

    def get_headers(self):
        return {
            'Authorization': f'Bearer {self.token}'
        }

    def send(self, channel, message):

        message = message[:3000]  # slack does not accept long messages

        params = {
            'channel': channel,
            'text': message
        }
        response = requests.post(
            'https://slack.com/api/chat.postMessage',
            headers=self.get_headers(),
            params=params,
            timeout=10
        )
        response.raise_for_status()
