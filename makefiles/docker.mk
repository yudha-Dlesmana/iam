.PHONY: start stop reset

start:
	docker compose -f docker-compose-dev.yml up  -d

stop:
	docker compose stop

reset:
	docker compose down -v