
import json
import os

from google.cloud import storage

from airless.hook.base import BaseHook
from airless.hook.local.file import FileHook


from itertools import zip_longest


def natatime(n, iterable, fillvalue=None):
    stepped_slices = [iter(iterable)] * n
    return zip_longest(*stepped_slices, fillvalue=fillvalue)


class GcsHook(BaseHook):

    def __init__(self):
        super().__init__()
        self.storage_client = storage.Client()
        self.file_hook = FileHook()

    def build_filepath(self, bucket, filepath):
        return f'gs://{bucket}/{filepath}'

    def read(self, bucket, filepath, encoding=None):
        bucket = self.storage_client.get_bucket(bucket)

        blob = bucket.blob(filepath)
        content = blob.download_as_string()
        if encoding:
            content = content.decode(encoding)
        return content

    def read_json(self, bucket, filepath, encoding=None):
        return json.loads(self.read(bucket, filepath, encoding))

    def upload_from_memory(self, data, bucket, directory, filename, add_timestamp):
        local_filename = self.file_hook.get_tmp_filepath(filename, add_timestamp)
        self.file_hook.write(local_filename, data)
        self.upload(local_filename, bucket, directory)
        os.remove(local_filename)

    def upload(self, local_filepath, bucket, directory):
        filename = self.file_hook.extract_filename(local_filepath)
        bucket = self.storage_client.bucket(bucket)
        blob = bucket.blob(f"{directory}/{filename}")
        blob.upload_from_filename(local_filepath)

    def check_existance(self, bucket, filepath):
        blobs = self.storage_client.list_blobs(bucket, prefix=filepath, max_results=1, page_size=1)
        return len(list(blobs)) > 0

    def move(self, from_bucket, from_prefix, to_bucket, to_directory):
        bucket = self.storage_client.get_bucket(from_bucket)
        blobs = bucket.list_blobs(prefix=from_prefix)

        dest_bucket = self.storage_client.bucket(to_bucket)

        for blob in blobs:
            if not blob.name.endswith('/'):
                filename = blob.name.split('/')[-1]
                bucket.copy_blob(
                    blob, dest_bucket, f'{to_directory}/{filename}'
                )
                bucket.delete_blob(blob.name)

    def delete(self, bucket_name, prefix):
        bucket = self.storage_client.get_bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)

        for to_delete_batch in natatime(100, blobs):
            tmp_list = [tdb for tdb in to_delete_batch if (tdb is not None) and (tdb.name != prefix)]
            if len(tmp_list) > 0:
                with self.storage_client.batch():
                    for blob in tmp_list:
                        blob.delete()
