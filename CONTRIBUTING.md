# How to contribute
---

## Flow
1. Create branch and develop `features`/`bugfixes`/`hotfix`
2. Describe the changes into `CHANGELOG.md` under `unreleased`
3. Publish a pypi dev version and test it
4. Create a pull request(PR) of that branch
5. After approved can merge it into `main`
6. If have more changes do in another branch following the steps above.
7. After all changes planned was done, create a new branch named `realease-v<VERSION>`
8. Execute de `bumpversion` using `makefile` command
9. Push the branch to origin and open a PR
10. After approved, merge it
11. Create a github realease from tag, and copy the changes made for that version from `CHANGELOG.md`

# How to publish pypi dev version
- Change version name in `pyproject.toml` and `setup.cfg`. The name pattern is `{major}.{minor}.{patch}.dev{version}`
- Execute make command `publish-dev-version`

## How to release bumpversion itself
Execute the following commands:

``` bash
make release-patch|release-minor|release-major
```
