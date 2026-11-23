.PHONY: install lint format test audit check

install:
	pip install -r requirements-dev.txt

lint:
	ruff check .
	ruff format --check .

format:
	ruff check --fix .
	ruff format .

test:
	pytest

audit:
	pip-audit -r requirements.txt

check: lint test
