
import json
import ndjson
import os
from typing import Any, List, Optional

from google.cloud import storage
from google.cloud.storage.retry import DEFAULT_RETRY
import pyarrow as pa
from pyarrow import parquet

from airless.core.hook import BaseHook, FileHook


class GcsHook(BaseHook):
    """Hook for interacting with Google Cloud Storage."""

    def __init__(self) -> None:
        """Initializes the GcsHook."""
        super().__init__()
        self.storage_client = storage.Client()
        self.file_hook = FileHook()

    def build_filepath(self, bucket: str, filepath: str) -> str:
        """Builds the full GCS file path.

        Args:
            bucket (str): The name of the GCS bucket.
            filepath (str): The file path.

        Returns:
            str: The full GCS file path.
        """
        return f'gs://{bucket}/{filepath}'

    def read_as_string(self, bucket: str, filepath: str, encoding: Optional[str] = None) -> str:
        """Reads a file from GCS as a string.

        Args:
            bucket (str): The name of the GCS bucket.
            filepath (str): The file path.
            encoding (Optional[str]): The encoding to use. Defaults to None.

        Returns:
            str: The content of the file as a string.
        """
        bucket = self.storage_client.get_bucket(bucket)

        blob = bucket.blob(filepath)
        content = blob.download_as_string()
        if encoding:
            return content.decode(encoding)
        else:
            return content.decode()

    def read_as_bytes(self, bucket: str, filepath: str) -> bytes:
        """Reads a file from GCS as bytes.

        Args:
            bucket (str): The name of the GCS bucket.
            filepath (str): The file path.

        Returns:
            bytes: The content of the file as bytes.
        """
        bucket = self.storage_client.get_bucket(bucket)

        blob = bucket.blob(filepath)
        return blob.download_as_bytes()

    def download(self, bucket: str, filepath: str, target_filepath: Optional[str] = None) -> None:
        """Downloads a file from GCS.

        Args:
            bucket (str): The name of the GCS bucket.
            filepath (str): The file path.
            target_filepath (Optional[str]): The target file path. Defaults to None.
        """
        bucket = self.storage_client.get_bucket(bucket)

        filename = filepath.split('/')[-1]
        blob = bucket.blob(filepath)
        blob.download_to_filename(target_filepath or filename)

    def read_json(self, bucket: str, filepath: str, encoding: Optional[str] = None) -> Any:
        """Reads a JSON file from GCS.

        Args:
            bucket (str): The name of the GCS bucket.
            filepath (str): The file path.
            encoding (Optional[str]): The encoding to use. Defaults to None.

        Returns:
            Any: The content of the JSON file.
        """
        return json.loads(self.read_as_string(bucket, filepath, encoding))

    def read_ndjson(self, bucket: str, filepath: str, encoding: Optional[str] = None) -> List[Any]:
        """Reads an NDJSON file from GCS.

        Args:
            bucket (str): The name of the GCS bucket.
            filepath (str): The file path.
            encoding (Optional[str]): The encoding to use. Defaults to None.

        Returns:
            List[Any]: The content of the NDJSON file.
        """
        return ndjson.loads(self.read_as_string(bucket, filepath, encoding))

    def upload_from_memory(
            self,
            data: Any,
            bucket: str,
            directory: str,
            filename: str,
            **kwargs: Any
        ) -> str:
        """Uploads data from memory to GCS.

        Args:
            data (Any): The data to upload.
            bucket (str): The name of the GCS bucket.
            directory (str): The directory within the bucket.
            filename (str): The name of the file to create.

        Kwargs:
            add_timestamp (bool, optional): If True, adds a timestamp to the filename. Defaults to True.
            use_ndjson (bool, optional): If True, writes data in NDJSON format. Defaults to False.
            mode (str, optional): The mode for opening the file. Defaults to 'w'.

        Returns:
            str: The path to the uploaded file.
        """
        local_filename = self.file_hook.get_tmp_filepath(filename, **kwargs)
        try:
            self.file_hook.write(local_filename, data, **kwargs)
            return self.upload(local_filename, bucket, directory)

        finally:
            if os.path.exists(local_filename):
                os.remove(local_filename)

    def upload_parquet_from_memory(
            self,
            data: Any,
            bucket: str,
            directory: str,
            filename: str,
            **kwargs: Any
        ) -> str:
        """Uploads Parquet data from memory to GCS.

        Args:
            data (Any): The data to upload.
            bucket (str): The name of the GCS bucket.
            directory (str): The directory within the bucket.
            filename (str): The name of the Parquet file to create.

        Kwargs:
            schema (pa.Schema, optional): The schema for the Parquet table. Defaults to None.
            add_timestamp (bool, optional): If True, adds a timestamp to the filename. Defaults to True.

        Returns:
            str: The path to the uploaded Parquet file.
        """
        schema = kwargs.get('schema', None)

        local_filename = self.file_hook.get_tmp_filepath(filename, **kwargs)

        try:
            table = pa.Table.from_pylist(data, schema=schema)
            pool = pa.default_memory_pool()

            parquet.write_table(
                table,
                local_filename,
                compression='GZIP'
            )

            del table
            pool.release_unused()

            return self.upload(local_filename, bucket, directory)
        finally:
            if os.path.exists(local_filename):
                os.remove(local_filename)

    def upload(self, local_filepath: str, bucket_name: str, directory: str) -> str:
        """Uploads a local file to GCS.

        Args:
            local_filepath (str): The path to the local file.
            bucket_name (str): The name of the GCS bucket.
            directory (str): The directory within the bucket.

        Returns:
            str: The path to the uploaded file in GCS.
        """
        filename = self.file_hook.extract_filename(local_filepath)
        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(f"{directory}/{filename}")
        blob.upload_from_filename(local_filepath)
        return f"{bucket_name}/{directory}/{filename}"

    def upload_folder(self, local_path: str, bucket: str, gcs_path: str) -> None:
        """Uploads a folder to GCS.

        Args:
            local_path (str): The local folder path.
            bucket (str): The name of the GCS bucket.
            gcs_path (str): The GCS path to upload to.
        """
        for root, _, files in os.walk(local_path):
            for file in files:
                local_file_path = os.path.join(root, file)
                gcs_blob_name = os.path.join(gcs_path, os.path.relpath(local_file_path, local_path))

                # Upload the file to GCS
                bucket_ = self.storage_client.bucket(bucket)
                blob = bucket_.blob(gcs_blob_name)
                blob.upload_from_filename(local_file_path)

    def check_existance(self, bucket: str, filepath: str) -> bool:
        """Checks if a file exists in GCS.

        Args:
            bucket (str): The name of the GCS bucket.
            filepath (str): The file path.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        blobs = self.storage_client.list_blobs(bucket, prefix=filepath, max_results=1, page_size=1)
        return len(list(blobs)) > 0

    def move(self, from_bucket: str, from_prefix: str, to_bucket: str, to_directory: str, rewrite: bool) -> None:
        """Moves files from one GCS location to another.

        Args:
            from_bucket (str): The source bucket.
            from_prefix (str): The source prefix.
            to_bucket (str): The destination bucket.
            to_directory (str): The destination directory.
            rewrite (bool): Whether to overwrite existing files.
        """
        bucket = self.storage_client.get_bucket(from_bucket)
        dest_bucket = self.storage_client.bucket(to_bucket)

        blobs = list(bucket.list_blobs(prefix=from_prefix, fields='items(name),nextPageToken'))
        self.move_blobs(bucket, blobs, dest_bucket, to_directory, rewrite)

    def move_files(self, from_bucket: str, files: List[str], to_bucket: str, to_directory: str, rewrite: bool) -> None:
        """Moves specified files from one GCS location to another.

        Args:
            from_bucket (str): The source bucket.
            files (List[str]): The list of files to move.
            to_bucket (str): The destination bucket.
            to_directory (str): The destination directory.
            rewrite (bool): Whether to overwrite existing files.
        """
        bucket = self.storage_client.get_bucket(from_bucket)
        dest_bucket = self.storage_client.bucket(to_bucket)

        blobs = self.files_to_blobs(bucket, files)
        self.move_blobs(bucket, blobs, dest_bucket, to_directory, rewrite)

    def move_blobs(self, bucket: storage.Bucket, blobs: List[storage.Blob], to_bucket: storage.Bucket, to_directory: str, rewrite: bool) -> None:
        """Moves blobs from one bucket to another.

        Args:
            bucket (storage.Bucket): The source bucket.
            blobs (List[storage.Blob]): The list of blobs to move.
            to_bucket (storage.Bucket): The destination bucket.
            to_directory (str): The destination directory.
            rewrite (bool): Whether to overwrite existing files.
        """
        if rewrite:
            self.rewrite_blobs(blobs, to_bucket, to_directory)
        else:
            self.copy_blobs(bucket, blobs, to_bucket, to_directory)

        self.delete_blobs(blobs)

    def rewrite_blobs(self, blobs: List[storage.Blob], to_bucket: storage.Bucket, to_directory: str) -> None:
        """Rewrites blobs in the destination bucket.

        Args:
            blobs (List[storage.Blob]): The list of blobs to rewrite.
            to_bucket (storage.Bucket): The destination bucket.
            to_directory (str): The destination directory.
        """
        for blob in blobs:
            if not blob.name.endswith('/'):
                rewrite_token = False
                filename = blob.name.split('/')[-1]

                dest_blob = to_bucket.blob(f'{to_directory}/{filename}')
                while True:
                    rewrite_token, bytes_rewritten, bytes_to_rewrite = dest_blob.rewrite(
                        source=blob,
                        token=rewrite_token,
                        retry=DEFAULT_RETRY
                    )
                    self.logger.debug(f'{to_directory}/{filename} - Progress so far: {bytes_rewritten}/{bytes_to_rewrite} bytes')

                    if not rewrite_token:
                        break

    def copy_blobs(self, bucket: storage.Bucket, blobs: List[storage.Blob], to_bucket: storage.Bucket, to_directory: str) -> None:
        """Copies blobs from one bucket to another.

        Args:
            bucket (storage.Bucket): The source bucket.
            blobs (List[storage.Blob]): The list of blobs to copy.
            to_bucket (storage.Bucket): The destination bucket.
            to_directory (str): The destination directory.
        """
        batch_size = 100
        count = 0

        while count < len(blobs):
            with self.storage_client.batch():
                for blob in blobs[count:count + batch_size]:
                    if not blob.name.endswith('/'):
                        filename = blob.name.split('/')[-1]
                        bucket.copy_blob(
                            blob=blob,
                            destination_bucket=to_bucket,
                            new_name=f'{to_directory}/{filename}',
                            retry=DEFAULT_RETRY
                        )
                count = count + batch_size

    def delete(self, bucket_name: str, prefix: Optional[str] = None, files: Optional[List[str]] = None) -> None:
        """Deletes files from GCS.

        Args:
            bucket_name (str): The name of the GCS bucket.
            prefix (Optional[str]): The prefix for files to delete. Defaults to None.
            files (Optional[List[str]]): The list of specific files to delete. Defaults to None.
        """
        bucket = self.storage_client.get_bucket(bucket_name)
        if files:
            blobs = self.files_to_blobs(bucket, files)
        else:
            blobs = list(bucket.list_blobs(prefix=prefix, fields='items(name),nextPageToken'))

        self.delete_blobs(blobs)

    def delete_blobs(self, blobs: List[storage.Blob]) -> None:
        """Deletes a list of blobs.

        Args:
            blobs (List[storage.Blob]): The list of blobs to delete.
        """
        batch_size = 100
        count = 0

        while count < len(blobs):
            with self.storage_client.batch():
                for blob in blobs[count:count + batch_size]:
                    self.logger.debug(f'Deleting blob {blob.name}')
                    blob.delete(retry=DEFAULT_RETRY)
                count = count + batch_size

    def list(self, bucket_name: str, prefix: Optional[str] = None) -> List[storage.Blob]:
        """Lists blobs in a GCS bucket.

        Args:
            bucket_name (str): The name of the GCS bucket.
            prefix (Optional[str]): The prefix to filter blobs. Defaults to None.

        Returns:
            List[storage.Blob]: The list of blobs.
        """
        return self.storage_client.list_blobs(
            bucket_name,
            prefix=prefix,
            fields='items(name,size,timeCreated,timeDeleted),nextPageToken'
        )

    def files_to_blobs(self, bucket: storage.Bucket, files: List[str]) -> List[storage.Blob]:
        """Converts a list of file names to blobs.

        Args:
            bucket (storage.Bucket): The GCS bucket.
            files (List[str]): The list of file names.

        Returns:
            List[storage.Blob]: The list of blobs.
        """
        return [bucket.blob(f) for f in files]
