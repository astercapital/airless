
import json
import ndjson
import os
import requests

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

    def download(self, url, headers, timeout=500, proxies=None):
        local_filename = self.get_tmp_filepath(url)
        with requests.get(url, stream=True, verify=False, headers=headers, timeout=timeout, proxies=proxies) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return local_filename

    def rename(self, from_filename, to_filename):
        to_filename_formatted = ('' if to_filename.startswith('/tmp/') else '/tmp/') + to_filename
        os.rename(from_filename, to_filename_formatted)
        return to_filename_formatted

    def rename_files(self, dir, prefix):
        for root, subdirs, files in os.walk(dir):
            for filename in files:
                os.rename(os.path.join(root, filename), os.path.join(root, f'{prefix}_{filename}'))

    def list_files(self, folder):
        file_list = []
        for root, subdirs, files in os.walk(folder):
            for filename in files:
                filepath = os.path.join(root, filename)
                file_list.append(filepath)

        return file_list
