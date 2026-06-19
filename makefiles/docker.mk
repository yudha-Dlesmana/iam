.PHONY: start stop reset

start:
	docker compose -f docker-compose-dev.yml up  -d

stop:
	docker compose -f docker-compose-dev.yml stop

reset:
	docker compose -f docker-compose-dev.yml down -v