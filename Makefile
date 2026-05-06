.PHONY: dev down stop reset logs logs-mysql logs-redis

dev:
	@chmod +x bin/start.sh
	@./bin/start.sh

stop:
	docker compose stop

down:
	docker compose down
	
reset:
	docker compose down -v
	
logs:
	docker compose logs -f

logs-mysql:
	docker compose logs -f mysql

logs-redis:
	docker compose logs -f redis
