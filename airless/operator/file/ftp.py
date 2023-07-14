
import os

from airless.hook.file.ftp import FtpHook
from airless.operator.file.file import FileUrlToGcsOperator


class FtpToGcsOperator(FileUrlToGcsOperator):

    def __init__(self):
        super().__init__()
        self.ftp_hook = FtpHook()

    def execute(self, data, topic):
        origin = data['origin']
        destination = data['destination']

        self.ftp_hook = FtpHook()
        self.ftp_hook.login(origin['host'], origin.get('user'), origin.get('pass'))

        local_filepath = self.ftp_hook.download(origin['directory'], origin['filename'])

        self.move_to_destinations(local_filepath, destination)

        os.remove(local_filepath)
