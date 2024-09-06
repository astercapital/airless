
import re

from dateutil import parser
from ftplib import FTP

from airless.hook.file.file import FileHook


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
