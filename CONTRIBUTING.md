# How to contribute
---

## How to release bumpversion itself
Execute the following commands:

``` bash
git checkout master
git pull
make test
make lint
bump2version release
make dist
make upload
bump2version --no-tag patch
git push origin master --tags
```
