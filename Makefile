include makefiles/deploy.mk

.PHONY: help

help:
		@echo 'Deploy:		make deploy | update | up-prod | down-prod '
		@echo 'Logs:		make logs-prod | logs-caddy '
		@echo 'Restart:		make restart-prod | restart-caddy '