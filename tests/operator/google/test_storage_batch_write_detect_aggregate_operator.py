import pytest
from datetime import datetime, timedelta, timezone
from airless.operator.google.storage import BatchWriteDetectAggregateOperator, ProcessTopic
from unittest.mock import MagicMock
from google.api_core.exceptions import NotFound


@pytest.fixture
def operator():
    op = BatchWriteDetectAggregateOperator()
    op.process_and_reset_table = MagicMock()
    op.send_to_process = MagicMock()
    op.gcs_hook = MagicMock()
    op.document_db_folder = 'test_folder'
    op.partially_processed_tables = []
    op.tables_last_timestamp_processed = {}
    return op

class MockBlob:
    def __init__(self, time_created, time_deleted=None, size=None):
        self.time_created = time_created
        self.time_deleted = time_deleted
        self.size = size



####### is_processing_required
# Use case 1: blob was created after the last timestamp and before the deadline
def test_blob_created_after_last_before_deadline(operator):
    last_timestamp = datetime.now(timezone.utc) - timedelta(minutes=120)
    within_deadline_blob = MockBlob(datetime.now(timezone.utc) - timedelta(minutes=30))
    assert operator.is_processing_required(within_deadline_blob, last_timestamp, 60)

# Use case 2: blob was created after the last timestamp and after the deadline
def test_blob_created_after_last_after_deadline(operator):
    last_timestamp = datetime.now(timezone.utc) - timedelta(minutes=120)
    outside_deadline_blob = MockBlob(datetime.now(timezone.utc) - timedelta(minutes=90))
    assert operator.is_processing_required(outside_deadline_blob, last_timestamp, 60)

# Use case 3: blob was created before the last timestamp and before the deadline
def test_blob_created_before_last_before_deadline(operator):
    last_timestamp = datetime.now(timezone.utc) - timedelta(minutes=15)
    within_deadline_but_before_last_timestamp_blob = MockBlob(datetime.now(timezone.utc) - timedelta(minutes=30))
    assert not operator.is_processing_required(within_deadline_but_before_last_timestamp_blob, last_timestamp, 60)

# Use case 4: blob was created before the last timestamp and after the deadline
def test_blob_created_before_last_after_deadline(operator):
    last_timestamp = datetime.now(timezone.utc) - timedelta(minutes=30)
    outside_deadline_and_before_last_timestamp_blob = MockBlob(datetime.now(timezone.utc) - timedelta(minutes=90))
    assert operator.is_processing_required(outside_deadline_and_before_last_timestamp_blob, last_timestamp, 60)

# Use case 5: blob was deleted
def test_blob_was_deleted(operator):
    deleted_blob = MockBlob(datetime.now(timezone.utc) - timedelta(minutes=30), datetime.now(timezone.utc))
    assert not operator.is_processing_required(deleted_blob, datetime.min.replace(tzinfo=timezone.utc), 60)



####### update_table_records
# Use case 1: Updating a table with a new blob when the table is initially empty
def test_update_table_records_new_blob_empty_table(operator):
    blob = MockBlob(datetime.now(timezone.utc), size=100)
    operator.update_table_records(blob, 'test_table', 'file1.txt')
    assert operator.tables['test_table']['size'] == 100
    assert operator.tables['test_table']['files'] == ['file1.txt']
    assert operator.tables['test_table']['min_time_created'] == blob.time_created
    assert operator.tables['test_table']['max_time_created'] == blob.time_created

# Use case 2: Updating a table with a new blob when the table already has records
def test_update_table_records_new_blob_existing_table(operator):
    initial_blob = MockBlob(datetime.now(timezone.utc) - timedelta(minutes=5), size=100)
    operator.update_table_records(initial_blob, 'test_table', 'initial_file.txt')
    new_blob = MockBlob(datetime.now(timezone.utc), size=200)
    operator.update_table_records(new_blob, 'test_table', 'new_file.txt')
    assert operator.tables['test_table']['size'] == 300  # 100 + 200
    assert operator.tables['test_table']['files'] == ['initial_file.txt', 'new_file.txt']
    assert operator.tables['test_table']['min_time_created'] == initial_blob.time_created
    assert operator.tables['test_table']['max_time_created'] == new_blob.time_created

# Use case 3: Correctly updating the min and max time created for blobs
def test_update_table_records_min_max_time(operator):
    old_blob = MockBlob(datetime.now(timezone.utc) - timedelta(days=1), size=50)
    operator.update_table_records(old_blob, 'test_table', 'old_file.txt')
    new_blob = MockBlob(datetime.now(timezone.utc), size=150)
    operator.update_table_records(new_blob, 'test_table', 'new_file.txt')
    assert operator.tables['test_table']['min_time_created'] == old_blob.time_created
    assert operator.tables['test_table']['max_time_created'] == new_blob.time_created

# Use case 4: Ensuring size and files list are updated correctly
def test_update_table_records_size_files_update(operator):
    blobs = [MockBlob(datetime.now(timezone.utc) - timedelta(minutes=i*10), size=size) for i, size in enumerate([100, 200, 300])]
    filenames = ['file1.txt', 'file2.txt', 'file3.txt']
    total_size = sum(blob.size for blob in blobs)
    for blob, filename in zip(blobs, filenames):
        operator.update_table_records(blob, 'test_table', filename)
    assert operator.tables['test_table']['size'] == total_size
    assert operator.tables['test_table']['files'] == filenames



####### check_and_send_for_processing
# Use case 1: Table size exceeds the medium size threshold
def test_check_and_send_size_exceeds_medium(operator):
    table_key = 'test_table'
    operator.tables[table_key] = {'size': 1100, 'files': ['file1.txt', 'file2.txt'], 'min_time_created': datetime.now(timezone.utc), 'max_time_created': datetime.now(timezone.utc)}
    config = {
        'threshold': {'size_medium': 1000, 'size_small': 500, 'file_quantity': 5},
        'bucket': 'test_bucket'
    }
    operator.check_and_send_for_processing(table_key, config)
    operator.process_and_reset_table.assert_called_with(table_key, config['bucket'], 'RAW', ProcessTopic.MEDIUM)

# Use case 2: Number of files exceeds the file quantity threshold, size below small size threshold
def test_check_and_send_files_exceed_quantity_size_below_small(operator):
    table_key = 'test_table'
    operator.tables[table_key] = {'size': 400, 'files': ['file1.txt', 'file2.txt', 'file3.txt', 'file4.txt', 'file5.txt', 'file6.txt'], 'min_time_created': datetime.now(timezone.utc), 'max_time_created': datetime.now(timezone.utc)}
    config = {
        'threshold': {'size_medium': 1000, 'size_small': 500, 'file_quantity': 5},
        'bucket': 'test_bucket'
    }
    operator.check_and_send_for_processing(table_key, config)
    operator.process_and_reset_table.assert_called_with(table_key, config['bucket'], config['bucket'], ProcessTopic.SMALL)

# Use case 3: Number of files exceeds the file quantity threshold, size above small size threshold
def test_check_and_send_files_exceed_quantity_size_above_small(operator):
    table_key = 'test_table'
    operator.tables[table_key] = {'size': 600, 'files': ['file1.txt', 'file2.txt', 'file3.txt', 'file4.txt', 'file5.txt', 'file6.txt'], 'min_time_created': datetime.now(timezone.utc), 'max_time_created': datetime.now(timezone.utc)}
    config = {
        'threshold': {'size_medium': 1000, 'size_small': 500, 'file_quantity': 5},
        'bucket': 'test_bucket'
    }
    operator.check_and_send_for_processing(table_key, config)
    operator.process_and_reset_table.assert_called_with(table_key, config['bucket'], config['bucket'], ProcessTopic.MEDIUM)

# Use case 4: Neither size nor number of files exceed their thresholds
def test_check_and_send_no_threshold_exceeded(operator):
    table_key = 'test_table'
    operator.tables[table_key] = {'size': 450, 'files': ['file1.txt', 'file2.txt', 'file3.txt'], 'min_time_created': datetime.now(timezone.utc), 'max_time_created': datetime.now(timezone.utc)}
    config = {
        'threshold': {'size_medium': 1000, 'size_small': 500, 'file_quantity': 5},
        'bucket': 'test_bucket'
    }
    operator.check_and_send_for_processing(table_key, config)
    operator.process_and_reset_table.assert_not_called()



####### process_based_on_file_count
# Use case 1: Single file in directory, size below the small threshold, directory not partially processed
def test_process_single_file_small_size_not_partially_processed(operator):
    directory = 'test_directory'
    data = {
        'files': ['file1.txt'],
        'size': 400,  # Below the SMALL size threshold
        'min_time_created': datetime.now(timezone.utc) - timedelta(minutes=60),
    }
    config = {
        'threshold': {'size_small': 500},
        'bucket': 'test_bucket',
    }
    time_threshold = datetime.now(timezone.utc) - timedelta(minutes=30)

    operator.process_based_on_file_count(directory, data, config, time_threshold)
    operator.send_to_process.assert_called_once_with('test_bucket', 'RAW', directory, ['file1.txt'], ProcessTopic.SMALL)

# Use case 2: Multiple files in directory, size below the small threshold, directory not partially processed
def test_process_multiple_files_small_size_not_partially_processed(operator):
    directory = 'test_directory'
    data = {
        'files': ['file1.txt', 'file2.txt'],
        'size': 400,  # Below the SMALL size threshold
        'min_time_created': datetime.now(timezone.utc) - timedelta(minutes=60),
    }
    config = {
        'threshold': {'size_small': 500},
        'bucket': 'test_bucket',
    }
    time_threshold = datetime.now(timezone.utc) - timedelta(minutes=30)

    operator.process_based_on_file_count(directory, data, config, time_threshold)
    operator.send_to_process.assert_called_once_with('test_bucket', 'test_bucket', directory, ['file1.txt', 'file2.txt'], ProcessTopic.SMALL)

# Use case 3: Directory marked as partially processed, files created before threshold, size above small threshold
def test_process_partially_processed_directory_above_small_threshold(operator):
    directory = 'test_directory'
    operator.partially_processed_tables.append(directory)
    data = {
        'files': ['file1.txt', 'file2.txt'],
        'size': 600,  # Above the SMALL size threshold
        'min_time_created': datetime.now(timezone.utc) - timedelta(minutes=60),
    }
    config = {
        'threshold': {'size_small': 500},
        'bucket': 'test_bucket',
    }
    time_threshold = datetime.now(timezone.utc) - timedelta(minutes=30)

    operator.process_based_on_file_count(directory, data, config, time_threshold)
    operator.send_to_process.assert_called_once_with('test_bucket', 'test_bucket', directory, ['file1.txt', 'file2.txt'], ProcessTopic.MEDIUM)

# Use case 4: Directory marked as partially processed, files created before threshold, size below small threshold
def test_process_partially_processed_directory_below_small_threshold(operator):
    directory = 'test_directory'
    operator.partially_processed_tables.append(directory)
    data = {
        'files': ['file1.txt', 'file2.txt'],
        'size': 400,  # Below the SMALL size threshold
        'min_time_created': datetime.now(timezone.utc) - timedelta(minutes=60),
    }
    config = {
        'threshold': {'size_small': 500},
        'bucket': 'test_bucket',
    }
    time_threshold = datetime.now(timezone.utc) - timedelta(minutes=30)

    operator.process_based_on_file_count(directory, data, config, time_threshold)
    operator.send_to_process.assert_called_once_with('test_bucket', 'test_bucket', directory, ['file1.txt', 'file2.txt'], ProcessTopic.SMALL)



####### get_dataset_and_table_from_filepath
# Use case 1: Filepath represents a table_name
def test_get_data_when_filepath_is_a_table(operator):
    filepath = 'dataset/table_name'
    expected_dataset = 'dataset'
    expected_table = 'table_name'

    dataset, table = operator.get_dataset_and_table_from_filepath(filepath)

    assert dataset == expected_dataset, "Dataset should be an empty string for root directory files"
    assert table == expected_table, "Table name should be extracted correctly from root directory files"

# Use case 2: Filepath represents a file
def test_get_data_when_filepath_is_a_file(operator):
    filepath = 'dataset/table_name/filename.file'
    expected_folder = 'dataset/table_name'
    expected_filename = 'filename.file'

    folder, filename = operator.get_dataset_and_table_from_filepath(filepath)

    assert folder == expected_folder, "Dataset should be correctly identified for nested directories"
    assert filename == expected_filename, "Table name should be extracted correctly from nested directory paths"

# Use case 3: Filepath ends with a slash (indicating a directory)
def test_get_data_when_filepath_is_a_directory(operator):
    filepath = '/dataset/table_name/'
    expected_folder = '/dataset/table_name'
    expected_filename = ''

    folder, filename = operator.get_dataset_and_table_from_filepath(filepath)

    assert folder == expected_folder, "Dataset should be the entire path minus the trailing slash for directory paths"
    assert filename == expected_filename, "Table should be an empty string when filepath ends with a slash"



####### verify_table_last_timestamp_processed
# Use case 1: Timestamp is available in memory
def test_verify_timestamp_in_memory(operator):
    directory = 'existing_in_memory_dataset/existing_in_memory_table'
    expected_timestamp = datetime.now().replace(tzinfo=timezone.utc)
    operator.tables_last_timestamp_processed[directory] = expected_timestamp

    timestamp = operator.verify_table_last_timestamp_processed(directory)

    assert timestamp == expected_timestamp

# Use case 2: Timestamp is fetched from bucket
def test_verify_timestamp_fetched_from_bucket(operator):
    directory = 'existing_in_bucket_dataset/existing_in_bucket_table'
    expected_timestamp_str = '20230315010101'
    expected_timestamp_obj = datetime.strptime(expected_timestamp_str, '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
    operator.gcs_hook.read_json.return_value = {'processed_at': expected_timestamp_str}

    timestamp = operator.verify_table_last_timestamp_processed(directory)

    assert timestamp == expected_timestamp_obj

# Use case 3: NotFound exception handled gracefully
def test_verify_timestamp_not_found_exception(operator):
    directory = 'missing_directory'
    operator.gcs_hook.read_json.side_effect = NotFound('Test not found error')

    timestamp = operator.verify_table_last_timestamp_processed(directory)

    assert timestamp == datetime.min.replace(tzinfo=timezone.utc)
