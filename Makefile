generate-docs:
	@python scripts/generate_docs.py
	@gendocs --config mkgendocs.yaml

serve-docs:
	@mkdocs serve
