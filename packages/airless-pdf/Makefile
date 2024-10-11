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
	@python -m build
	@echo "Upload package to pypi"
	@twine upload dist/*

lint:
	@make clean
	@flake8 airless --count --show-source --statistics

test:
	@make clean
	@LOG_LEVEL=DEBUG \
	GCS_BUCKET_RAW_ZONE=RAW \
	GCS_BUCKET_DOCUMENT_DB=DOCUMENT_DB \
	pytest tests

clean:
	@find . -type d -name '__pycache__' -exec rm -r {} +
