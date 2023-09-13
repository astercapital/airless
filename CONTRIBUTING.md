# How to contribute
---

## Flow
1. Create branch and develop `features`/`bugfixes`/`hotfix`
2. Describe the changes into `CHANGELOG.md` under `unreleased`
2. Create a pull request(PR) of that branch
3. After approved can merge it into `main`
4. If have more changes do in another branch following the steps above.
5. After all changes planned was done, create a new branch named `realease-v<VERSION>`
6. Execute de `bumpversion` using `makefile` command
7. Push the branch to origin and open a PR
8. After approved, merge it
9. Create a github realease from tag, and copy the changes made for that version from `CHANGELOG.md`

## How to release bumpversion itself
Execute the following commands:

``` bash
make release-patch|release-minor|release-major
```
