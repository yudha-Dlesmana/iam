alembic command

generate migration
alembic revision --autogenerate -m "description"

apply migration
alembic upgrade head