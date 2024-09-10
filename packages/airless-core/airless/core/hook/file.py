
import json
import ndjson
import os
import requests
import uuid
import re
from dateutil import parser
from ftplib import FTP

from datetime import datetime

from airless.core.hook import BaseHook


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
            filename = f"{timestamp}_{uuid.uuid4().hex}_{filename}"
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


class FtpHook(FileHook):

    def __init__(self):
        super().__init__()
        self.ftp = None

    def login(self, host, user, password):
        self.ftp = FTP(host, user, password)
        self.ftp.login()

    def cwd(self, dir):
        if dir:
            self.ftp.cwd(dir)

    def list(self, regex=None, updated_after=None, updated_before=None):
        lines = []
        self.ftp.dir("", lines.append)

        files = []
        directories = []

        for line in lines:
            tokens = line.split()
            obj = {
                'name': tokens[3],
                'updated_at': parser.parse(' '.join(tokens[:1]))
            }

            if regex and not re.search(regex, obj['name'], re.IGNORECASE):
                continue

            if updated_after and not (obj['updated_at'] >= updated_after):
                continue

            if updated_before and not (obj['updated_at'] <= updated_before):
                continue

            obj = {
                'name': tokens[3],
                'updated_at': parser.parse(' '.join(tokens[:1]))
            }
            if tokens[2] == '<DIR>':
                directories.append(obj)
            else:
                files.append(obj)

        return files, directories

    def download(self, dir, filename):
        self.cwd(dir)
        local_filepath = self.get_tmp_filepath(filename)
        with open(local_filepath, 'wb') as file:
            self.ftp.retrbinary(f'RETR {filename}', file.write)
        return local_filepath
