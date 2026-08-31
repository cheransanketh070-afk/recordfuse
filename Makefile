.PHONY: install test lint format typecheck audit build quality demo

install:
	python -m pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy src/recordfuse

audit:
	pip-audit

build:
	python -m build

quality: lint typecheck test build

demo:
	recordfuse reconcile --input examples/crm.csv --input examples/billing.csv --output reconciled.json
