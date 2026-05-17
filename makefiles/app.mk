PYTHON := .venv/bin/python3
PIP := .venv/bin/pip

.PHONY: install run

install:
	$(PIP) install -r requirements.txt

run:
	$(PYTHON) main.py