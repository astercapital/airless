
**unreleased**
- [Bugfix] Refactor Google operators to inherit from `GoogleBaseEventOperator`, ensuring proper error handling and consistent use of the `queue_hook` attribute

**v0.1.0**
- [Refactor] Update requirements.txt to get new `airless-core` version `0.2.1`

**v0.0.5**
- [Bugfix] Add `GCP_PROJECT` param to secret manager get_secret calls

**v0.0.4**
- [Bugfix] Add dynamic dependencies from `requirements.txt` to `pyproject.toml`
- [Feature] Create a new command to generate automatically a tag to deploy a new package version
- [Feature] Automatically generate git tag when bumpversion is triggered
- [Refactor] Add package name to bumpversion commit message

**v0.0.3**
- [Refactor] Move all build configurations to `pyproject.toml`
- [Refactor] Remove `__init__.py` from root namespace
- [Refactor] add `__all__` object to reference package classes
- [Refactor] Change linter from `flake8` to `ruff`

**v0.0.2**
- [Feature] Enhance dependencies

**v0.0.1**
- [Feature] Package created

**v0.0.0**