.PHONY: start stop reset

start:
	docker compose up -d

stop:
	docker compose stop

reset:
	docker compose down -v