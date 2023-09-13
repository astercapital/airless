release-patch:
	@bumpversion patch
	@git push origin --tags

release-minor:
	@bumpversion minor
	@git push origin --tags

release-major:
	@bumpversion major
	@git push origin --tags