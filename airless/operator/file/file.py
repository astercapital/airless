
import os
import re

from airless.hook.file.file import FileHook
from airless.hook.google.storage import GcsHook
from airless.operator.base import BaseEventOperator


class FileUrlToGcsOperator(BaseEventOperator):

    def __init__(self):
        super().__init__()
        self.file_hook = FileHook()
        self.gcs_hook = GcsHook()

    def execute(self, data, topic):
        origin = data['origin']
        destination = data['destination']

        local_filepath = self.file_hook.download(
            url=origin['url'],
            headers=origin.get('headers'),
            timeout=origin.get('timeout', 500),
            proxies=origin.get('proxies')
        )

        self.move_to_destinations(local_filepath, destination)

        os.remove(local_filepath)

    def move_to_destinations(self, local_filepath, destination):

        original_filepath = local_filepath
        destinations = destination if isinstance(destination, list) else [destination]

        for dest in destinations:

            if dest.get('filename'):
                local_filepath = self.file_hook.rename(
                    from_filename=local_filepath,
                    to_filename=dest.get('filename'))

            bucket = dest['bucket']
            directory = dest.get('directory', f"{dest.get('dataset')}/{dest.get('table')}/{dest.get('mode')}")
            remove_null_byte = dest.get('remove_null_byte')
            regex = dest.get('regex', '.*')

            if re.search(regex, local_filepath, re.IGNORECASE):

                if remove_null_byte:
                    self.remove_null_byte(local_filepath)
                self.gcs_hook.upload(local_filepath, bucket, directory)

                if local_filepath != original_filepath:  # revert to original filename
                    local_filepath = self.file_hook.rename(
                        from_filename=local_filepath,
                        to_filename=original_filepath)

    def remove_null_byte(self, local_filepath):
        splits = local_filepath.split('/')
        tmp_file = '/'.join(splits[:-1] + ['tmp-' + splits[-1]])

        escaped_filepath = re.escape(local_filepath)

        response = os.system(f"tr -d '\\000' < {escaped_filepath} > {tmp_file} && mv {tmp_file} {escaped_filepath}")
        if response != 0:
            raise Exception('not able to remove null bytes')
