
**unreleased**
- [Refactor] Use [`deprecation`](https://pypi.org/project/deprecation/) to deprecate functions instead of custom decorator
- [Refactor] Schedule deprecation for `BatchWriteProcessOperator` to version `1.0.0`
- [Refactor] Move all build configurations to `pyproject.toml`
- [Refactor] Remove `__init__.py` from root namespace

**v0.0.5**
- [Feature] Change some methods in `GcsHook` to support `**kwargs` arguments

**v0.0.4**
- [Feature] Get method `get_config` to new path
- [Feature] Enhance dependencies

**v0.0.3**
- [Bugfix] Add `airless-google-cloud-core` as a dependency

**v0.0.2**
- [Feature] Add method `read_as_bytes` to `GcsHook` class
- [Change] Change method `read` from `GcsHook` class to `read_as_string`

**v0.0.1**
- [Feature] Package created

**v0.0.0**