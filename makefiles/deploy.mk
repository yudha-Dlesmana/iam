.PHONY: deploy update migrate-prod logs-prod logs-caddy ps-prod up-prod down-prod restart-prod restart-caddy secrets-edit

COMPOSE_PROD := docker compose -f docker-compose-prod.yml

deploy:
	bash scripts/deploy.sh

update:
	git pull origin production
	bash scripts/deploy.sh

migrate-prod:
	$(COMPOSE_PROD) --env-file runtime/.env run --rm migrate

logs-prod:
	$(COMPOSE_PROD) --env-file runtime/.env logs -f app

logs-caddy:
	$(COMPOSE_PROD) --env-file runtime/.env logs -f caddy

ps-prod:
	$(COMPOSE_PROD) --env-file runtime/.env ps

up-prod:
	$(COMPOSE_PROD) --env-file runtime/.env up

down-prod:
	$(COMPOSE_PROD) --env-file runtime/.env down

restart-prod:
	$(COMPOSE_PROD) --env-file runtime/.env restart app

restart-caddy:
	$(COMPOSE_PROD) --env-file runtime/.env restart caddy

secrets-edit:
	sops secrets/production.env
