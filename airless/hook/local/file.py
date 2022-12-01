
import json
import ndjson

from datetime import datetime
from random import randint

from airless.hook.base import BaseHook


class FileHook(BaseHook):

    def __init__(self):
        super().__init__()

    def write(self, local_filepath, data, use_ndjson=False):
        with open(local_filepath, 'w') as f:
            if isinstance(data, dict) or isinstance(data, list):
                if use_ndjson:
                    ndjson.dump(data, f)
                else:
                    json.dump(data, f)
            else:
                f.write(str(data))

    def extract_filename(self, filepath_or_url):
        return filepath_or_url.split('/')[-1].split('?')[0].split('#')[0]

    def get_tmp_filepath(self, filepath_or_url, add_timestamp=True):
        filename = self.extract_filename(filepath_or_url)
        if add_timestamp:
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f'{timestamp}_{randint(1, 100000000)}_{filename}'
        return f'/tmp/{filename}'
