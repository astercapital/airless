
from typing import List
import requests

from airless.google.cloud.storage.hook import GcsHook


class PasteBinHook(GcsHook):

    def __init__(self):
        super().__init__()
        self.raw_endpoint = 'https://pastebin.com/raw'
        self.urls = ['yqNkp3mR', 'vNrgNqbd']

    def list_ids(self) -> List[str]:
        # Return ids to get content
        return self.urls

    def get_content(self, id):
        # Get content from pastebin
        response = requests.get(
            f"{self.raw_endpoint}/{id}",
            timeout=20
        )
        response.raise_for_status()
        data = response.json()

        return data
