COMPOSE_PROD := docker compose -f docker-compose-prod.yml

.PHONY: deploy prod-update prod-up prod-down prod-restart prod-logs prod-migrate prod-ps

deploy:
	bash scripts/deploy.sh

prod-update:
	git pull
	bash scripts/deploy.sh

prod-up:
	$(COMPOSE_PROD) up -d

prod-down:
	$(COMPOSE_PROD) down

prod-restart:
	$(COMPOSE_PROD) restart app

prod-logs:
	$(COMPOSE_PROD) logs -f --tail=100

prod-migrate:
	$(COMPOSE_PROD) --profile tools run --rm migrate

prod-ps:
	$(COMPOSE_PROD) ps
