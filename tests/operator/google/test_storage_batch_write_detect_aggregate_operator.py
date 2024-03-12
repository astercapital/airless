import pytest
from datetime import datetime, timedelta, timezone
from airless.operator.google.storage import BatchWriteDetectAggregateOperator, ProcessTopic
from unittest.mock import MagicMock


@pytest.fixture
def operator():
    op = BatchWriteDetectAggregateOperator()
    op.process_and_reset_table = MagicMock()
    return op
    # return BatchWriteDetectAggregateOperator()

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
