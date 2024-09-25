
**unreleased**
- [Feature] Add new utils `enum` that have `baseEnum` class for basic list of objects selection class
- [Feature] Add `BaseLLMHook` to interact with LLMs
- [Feature] Change `config.py` from `airless` root to `utils` folder, for enhance the package structure

**v0.1.0**
- [Feature] Split modules into new packages

**v0.0.73**
- [Feature] Update `bigquery` package

**v0.0.72**
- [Feature] Return target filename after uploading data to GCS

**v0.0.71**
- [Feature] Allow file url to gcs operator to save file to a date partitioned directory structure

**v0.0.70**
- [Feature] Add namespace in setuptools

**v0.0.69**
- [Refactor] Remove old batch detect/aggregate functions
- [Feature] Add new service base class
- [Feature] Create deprecated decorators

**v0.0.68**
- [Feature] Return custom http response from operator
- [Feature] Do not execute next tasks if an error was thrown

**v0.0.67**
- [Refactor] Change GCS batch size to 100

**v0.0.66**
- [Refactor] Rewrite logic `BatchWriteDetectAggregateOperator` to be more clear
- [Feature] Write tests for `BatchWriteDetectAggregateOperator`

**v0.0.65**
- [Feature] Allow slack hook and operator to use parameters `response_url`, `response_type` and `replace_original`

**v0.0.64**
- [Feature] Add new parameter to process all files in bucket

**v0.0.63**
- [Feature] Allow email operator to use different SMTP secrets according to an env var

**v0.0.62**
- [Bugfix] Change directory from key to directory because key is the used in the previous for statement, directory is the current for statement

**v0.0.61**
- [Feature] Move files in `GcsHook` using batch operations to copy and delete files in order to improve performance
- [Feature] Add random hash to filename to increase upload velocity
- [Feature] Add logic to control which file timestamps are being processed

**v0.0.60**
- [Bugfix] In `BatchWriteProcessParquetOperator` change `send_to_processed_move` to use redirect function
- [Feature] Add `BatchAggregateParquetFilesOperator` class to agregate parquet files
- [Feature] Add `BatchWriteDetectAggregateOperator` class to compare file sizes and trigger `BatchAggregateParquetFilesOperator`
- [Feature] Change `send_to_landing_zone` to write parquet direct to gcs raw zone when `time_partition` is defined
- [Feature] Remove `BatchWriteDetectSizeOnlyOperator` because will not be used

**v0.0.59**
- [Feature] Add file size scale in `BatchWriteDetectSizeOnlyOperator` to allow processing of larger partitions

**v0.0.58**
- [Feature] Change from `BatchWriteProcessOrcOperator` to `BatchWriteProcessParquetOperator` to use parquet instead of orc

**v0.0.57**
- [Feature] Add support to `BatchWriteProcessOrcOperator` read ndjson

**v0.0.56**
- [Feature] Add partition logic on `send_to_landing_zone`
- [Feature] Remove partition logic from `BatchWriteProcessOrcOperator`

**v0.0.55**
- [Feature] Add the ability to send attachments in a slack message

**v0.0.53**
- [Feature] Create a new write detect operator with name `BatchWriteDetectSizeOnlyOperator` without the validation of the number of files
- [Feature] Create new operator `BatchWriteProcessOrcOperator` that write ORC file format

**v0.0.52**
- [Feature] Allow `BatchWriteDetectOperator` to receive a prefix to process only a few files

**v0.0.51**
- [Feature] Add `options` to method `build_success_message` in class `FileDetectOperator`, to allow pass generic arguments

**v0.0.50**
- [Feature] Add flow to `CONTRIBUTING.md`
- [Bugfix] Set max error timeout to 480 seconds

**v0.0.49**
- [Feature] Add automatically semantic version tags with `bump2version`
- [Feature] Add github action to get tag and publish to pypi
- [Feature] Add `CONTRIBUTING.md` and `CHANGELOG.md`

**Types of changes**
- [Feature]
- [Bugfix]
- [Hotfix]