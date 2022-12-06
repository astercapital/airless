
import json
import os

from datetime import datetime
from google.cloud import storage
from itertools import zip_longest

from airless.config import get_config
from airless.hook.base import BaseHook
from airless.hook.local.file import FileHook


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
            return content.decode(encoding)
        else:
            return content.decode()

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

    def move(self, from_bucket, from_prefix, to_bucket, to_directory, rewrite=False):
        bucket = self.storage_client.get_bucket(from_bucket)
        blobs = bucket.list_blobs(prefix=from_prefix)

        dest_bucket = self.storage_client.bucket(to_bucket)

        for blob in blobs:
            if not blob.name.endswith('/'):
                filename = blob.name.split('/')[-1]

                if rewrite:
                    rewrite_token = False
                    dest_blob = dest_bucket.blob(f'{to_directory}/{filename}')
                    while True:
                        rewrite_token, bytes_rewritten, bytes_to_rewrite = dest_blob.rewrite(
                            blob, token=rewrite_token)
                        self.logger.debug(f'{to_directory}/{filename} - Progress so far: {bytes_rewritten}/{bytes_to_rewrite} bytes')

                        if not rewrite_token:
                            break

                else:
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

    def list(self, bucket_name):
        return self.storage_client.list_blobs(bucket_name, fields='items(name,size,timeCreated,timeDeleted),nextPageToken')


class GcsDatalakeHook(GcsHook):

    def __init__(self):
        super().__init__()

    def build_metadata(self, message_id, origin):
        return {
            'event_id': message_id or 1234,
            'resource': origin or 'local'
        }

    def prepare_row(self, row, metadata):
        return {
            '_event_id': metadata['event_id'],
            '_resource': metadata['resource'],
            '_json': json.dumps({'data': row, 'metadata': metadata}),
            '_created_at': str(datetime.now())
        }

    def prepare_rows(self, data, metadata):
        prepared_rows = data if isinstance(data, list) else [data]
        return [self.prepare_row(row, metadata) for row in prepared_rows]

    def send_to_landing_zone(self, data, dataset, table, message_id, origin):

        if isinstance(data, list) and (len(data) == 0):
            raise Exception(f'Trying to send empty list to landing zone: {dataset}.{table}')

        if isinstance(data, dict) and (data == {}):
            raise Exception(f'Trying to send empty dict to landing zone: {dataset}.{table}')

        if get_config('ENV') == 'prod':
            metadata = self.build_metadata(message_id, origin)
            prepared_rows = self.prepare_rows(data, metadata)
            self.upload_from_memory(
                data=prepared_rows,
                bucket=get_config('GCS_BUCKET_LANDING_ZONE'),
                directory=f'{dataset}/{table}',
                filename='tmp.json',
                add_timestamp=True)
        else:
            self.logger.debug(f'[DEV] Uploading to {dataset}.{table}, Data: {data}')
