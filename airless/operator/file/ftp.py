
import os

from airless.hook.file.ftp import FtpHook
from airless.hook.google.storage import GcsHook
from airless.operator.base import BaseEventOperator


class FtpToGcsOperator(BaseEventOperator):

    def __init__(self):
        super().__init__()
        self.ftp_hook = FtpHook()
        self.gcs_hook = GcsHook()

    def execute(self, data, topic):
        origin = data['origin']
        destination = data['destination']

        self.ftp_hook = FtpHook()
        self.ftp_hook.login(origin['host'], origin.get('user'), origin.get('pass'))

        local_filepath = self.ftp_hook.download(origin['directory'], origin['filename'])

        destinations = destination if isinstance(destination, list) else [destination]
        for dest in destinations:
            bucket = dest['bucket']
            directory = dest.get('directory', f"{dest.get('dataset')}/{dest.get('table')}/{dest.get('mode')}")

            self.gcs_hook.upload(local_filepath, bucket, directory)

        os.remove(local_filepath)
