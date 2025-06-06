
PACKAGE_VERSION := $(shell grep -m 1 version pyproject.toml | tr -s ' ' | tr -d '"' | tr -d "'" | cut -d' ' -f3)
PACKAGE_NAME := $(shell grep -m 1 name pyproject.toml | tr -s ' ' | tr -d '"' | tr -d "'" | cut -d' ' -f3)

release-patch:
	@bumpversion patch

release-minor:
	@bumpversion minor

release-major:
	@bumpversion major

publish-dev-version:
	@read -p "Did you change version on pyproject.toml and add .dev1 in name? (yes/no): " answer; \
    if [ "$$answer" != "yes" ]; then \
        echo "Execution interrupted."; \
        exit 1; \
    fi
	@echo "Delete folders"
	@if [ -d "dist" ]; then rm -r dist/; fi && \
    for dir in *.egg-info; do \
    if [ -d "$$dir" ]; then rm -r "$$dir"; fi; \
    done
	@echo "Build package"
	@python3 -m build
	@echo "Upload package to pypi"
	@twine upload dist/*

lint:
	@make clean
	@ruff check --statistics

test:
	@make clean
	@LOG_LEVEL=DEBUG \
	GCS_BUCKET_RAW_ZONE=RAW \
	GCS_BUCKET_DOCUMENT_DB=DOCUMENT_DB \
	pytest tests

clean:
	@find . -type d -name '__pycache__' -exec rm -r {} +

tag:
	git tag $(PACKAGE_NAME)_v$(PACKAGE_VERSION)