
import json
import ndjson
import os
import logging

from datetime import datetime
from google.cloud import storage
from itertools import zip_longest
import pyarrow as pa
from pyarrow import parquet
from pyarrow import fs

from airless.config import get_config
from airless.hook.base import BaseHook
from airless.hook.file.file import FileHook


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

    def download(self, bucket, filepath, target_filepath=None):
        bucket = self.storage_client.get_bucket(bucket)

        filename = filepath.split('/')[-1]
        blob = bucket.blob(filepath)
        blob.download_to_filename(target_filepath or filename)

    def read_json(self, bucket, filepath, encoding=None):
        return json.loads(self.read(bucket, filepath, encoding))

    def read_ndjson(self, bucket, filepath, encoding=None):
        return ndjson.loads(self.read(bucket, filepath, encoding))

    def upload_from_memory(self, data, bucket, directory, filename, add_timestamp):
        local_filename = self.file_hook.get_tmp_filepath(filename, add_timestamp)
        try:
            self.file_hook.write(local_filename, data)
            self.upload(local_filename, bucket, directory)

        finally:
            if os.path.exists(local_filename):
                os.remove(local_filename)

    def upload_parquet_from_memory(self, data, bucket, directory, filename, add_timestamp, schema=None):
        gcs = fs.GcsFileSystem()
        table = pa.Table.from_pylist(data)
        table_casted = table.cast(schema) if schema else table
        local_filename = self.file_hook.get_tmp_filepath(filename, add_timestamp)
        local_filename = local_filename.split('/')[-1]

        parquet.write_table(
            table_casted,
            f'{bucket}/{directory}/{local_filename}',
            compression='GZIP',
            filesystem=gcs
        )

    def upload(self, local_filepath, bucket, directory):
        filename = self.file_hook.extract_filename(local_filepath)
        bucket = self.storage_client.bucket(bucket)
        blob = bucket.blob(f"{directory}/{filename}")
        blob.upload_from_filename(local_filepath)

    def upload_folder(self, local_path, bucket, gcs_path):
        for root, _, files in os.walk(local_path):
            for file in files:
                local_file_path = os.path.join(root, file)
                gcs_blob_name = os.path.join(gcs_path, os.path.relpath(local_file_path, local_path))

                # Upload the file to GCS
                bucket_ = self.storage_client.bucket(bucket)
                blob = bucket_.blob(gcs_blob_name)
                blob.upload_from_filename(local_file_path)

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

    def delete(self, bucket_name, prefix, files=None):
        bucket = self.storage_client.get_bucket(bucket_name)
        if files:
            blobs = [bucket.blob(f) for f in files] 
        else:
            blobs = bucket.list_blobs(prefix=prefix)

        for to_delete_batch in natatime(100, blobs):
            tmp_list = [tdb for tdb in to_delete_batch if (tdb is not None)]
            if len(tmp_list) > 0:
                with self.storage_client.batch():
                    for blob in tmp_list:
                        logging.info(f'Deleting blob {blob.name}')
                        blob.delete()

    def list(self, bucket_name, prefix=None):
        return self.storage_client.list_blobs(
            bucket_name,
            prefix=prefix,
            fields='items(name,size,timeCreated,timeDeleted),nextPageToken'
        )


class GcsDatalakeHook(GcsHook):

    def __init__(self):
        super().__init__()

    def build_metadata(self, message_id, origin):
        return {
            'event_id': message_id or 1234,
            'resource': origin or 'local'
        }

    def prepare_row(self, row, metadata, now):
        return {
            '_event_id': metadata['event_id'],
            '_resource': metadata['resource'],
            '_json': json.dumps({'data': row, 'metadata': metadata}),
            '_created_at': str(now)
        }

    def prepare_rows(self, data, metadata):
        now = datetime.now()
        prepared_rows = data if isinstance(data, list) else [data]
        return [self.prepare_row(row, metadata, now) for row in prepared_rows], now

    def send_to_landing_zone(self, data, dataset, table, message_id, origin, time_partition=False):

        if isinstance(data, list) and (len(data) == 0):
            raise Exception(f'Trying to send empty list to landing zone: {dataset}.{table}')

        if isinstance(data, dict) and (data == {}):
            raise Exception(f'Trying to send empty dict to landing zone: {dataset}.{table}')

        if get_config('ENV') == 'prod':
            metadata = self.build_metadata(message_id, origin)
            prepared_rows, now = self.prepare_rows(data, metadata)

            if time_partition:
                time_partition_name = 'date'
                schema = pa.schema([
                    ('_event_id', pa.int64()),
                    ('_resource', pa.string()),
                    ('_json', pa.string()),
                    ('_created_at', pa.timestamp('us'))
                ])
                self.upload_parquet_from_memory(
                    data=prepared_rows,
                    bucket=get_config('GCS_BUCKET_LANDING_ZONE'),
                    directory=f'{dataset}/{table}/{time_partition_name}={now.strftime("%Y-%m-%d")}',
                    filename='tmp.parquet',
                    add_timestamp=True,
                    schema=schema)
            else:
                self.upload_from_memory(
                    data=prepared_rows,
                    bucket=get_config('GCS_BUCKET_LANDING_ZONE'),
                    directory=f'{dataset}/{table}',
                    filename='tmp.json',
                    add_timestamp=True)
        else:
            self.logger.debug(f'[DEV] Uploading to {dataset}.{table}, Data: {data}')
