.PHONY: dev install test test-cov stop down reset logs logs-mysql logs-redis

dev:
	@chmod +x bin/start.sh
	@./bin/start.sh

install: 
	@test -d .venv || python3 -m venv .venv
	@.venv/bin/pip install --upgrade pip -r requirements.txt

test:
	@.venv/bin/pytest

test-cov:
	@.venv/bin/pytest --cov=src --cov-report=term-missing --cov-report=html

stop:
	docker compose stop
	
reset:
	docker compose down -v
	
logs:
	docker compose logs -f

logs-mysql:
	docker compose logs -f mysql

logs-redis:
	docker compose logs -f redis
