
**unreleased**

**v1.1.0**
- [Feature] Create method `recipient_string_to_array` in `GoogleEmailSendOperator` to transform recipients into an email array
- [Refactor] Remove placeholder `test_fake`

**v1.0.0**
- [Refactor] Get smtp secret from mounted secret instead of secret manager hook

**v0.1.0**
- [Refactor] Update requirements.txt to get new `airless-core` version `0.2.1`

**v0.0.6**
- [Feature] Create a new command to generate automatically a tag to deploy a new package version
- [Feature] Automatically generate git tag when bumpversion is triggered
- [Refactor] Add package name to bumpversion commit message
- [Bugfix] Add `GCP_PROJECT` param to secret manager get_secret calls

**v0.0.5**
- [Bugfix] Add dynamic dependencies from `requirements.txt` to `pyproject.toml`

**v0.0.4**
- [Refactor] Move all build configurations to `pyproject.toml`
- [Refactor] Remove `__init__.py` from root namespace
- [Refactor] add `__all__` object to reference package classes
- [Refactor] Change linter from `flake8` to `ruff`

**v0.0.3**
- [Feature] Get method `get_config` to new path
- [Feature] Enhance dependencies

**v0.0.2**
- [Feature] Fix changelogs

**v0.0.1**
- [Feature] Package created
