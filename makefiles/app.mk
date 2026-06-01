PYTHON := .venv/bin/python3
PIP := .venv/bin/pip
PYTEST := .venv/bin/pytest

.PHONY: install run test test-path test-cov gen-keys

install:
	$(PIP) install -r requirements.txt

run:
	$(PYTHON) main.py

test-path:
	${PYTEST} $(path) -v

test-cov:
	${PYTEST} --cov=src --cov-report=term-missing

gen-keys:
	bash scripts/gen_keys.sh iam-key-1