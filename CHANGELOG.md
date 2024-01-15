
**unreleased**

**unreleased**
- [Feature] Remove the validation of the number of files in `BatchWriteDetectOperator`
- [Feature] Rename operator `BatchWriteProcessOperator` to `BatchWriteProcessNdjsonOperator`
- [Feature] Create new operator `BatchWriteProcessOrcOperator` that write ORC file format
- [Feature] Create new operator `BatchWriteProcessedMoveOperator`
- [Feature] `BatchWriteProcessNdjsonOperator` use `BatchWriteProcessedMoveOperator` to move files

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