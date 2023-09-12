
build:
	python -m build

upload:
	twine upload dist/airless-0.0.42*

release-patch:
	@echo 'patch'

release-minor:
	@echo 'minor'

release-major:
	@echo 'major'