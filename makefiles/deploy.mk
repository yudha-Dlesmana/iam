.PHONY: deploy update migrate-prod logs-prod ps-prod up-prod down-prod restart-prod secrets-edit

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

ps-prod:
	$(COMPOSE_PROD) --env-file runtime/.env ps

up-prod:
	$(COMPOSE_PROD) --env-file runtime/.env up

down-prod:
	$(COMPOSE_PROD) --env-file runtime/.env down

restart-prod:
	$(COMPOSE_PROD) --env-file runtime/.env restart app

secrets-edit:
	sops secrets/production.env
