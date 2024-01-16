release-patch:
	@bumpversion patch
	@git push origin --tags

release-minor:
	@bumpversion minor
	@git push origin --tags

release-major:
	@bumpversion major
	@git push origin --tags

publish-dev-version:
	@read -p "Do you change version on pyproject.toml and add .dev1 in name? (yes/no): " answer; \
    if [ "$$answer" != "yes" ]; then \
        echo "Execution interrupted."; \
        exit 1; \
    fi
	@python -m build
	@twine upload dist/*