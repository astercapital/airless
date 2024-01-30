
**unreleased**

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