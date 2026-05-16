PYTHON := .venv/bin/python3
ALEMBIC := .venv/bin/alembic

.PHONY: db migrate upgrade downgrade seed setup

db:
	$(PYTHON) -m scripts.create_db

migrate:
	$(ALEMBIC) revision --autogenerate -m "$(m)"

upgrade:
	$(ALEMBIC) upgrade head

downgrade:
	$(ALEMBIC) downgrade -1

seed:
	$(PYTHON) -m scripts.seed

setup: db upgrade seed