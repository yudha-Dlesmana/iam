include makefiles/db.mk
include makefiles/docker.mk
include makefiles/app.mk
include makefiles/deploy.mk

.PHONY: help

help:
		@echo 'DB:			make migrate m=... | update | downgrade | seed '
		@echo 'Docker:		make start | stop | reset'
		@echo 'App: 		make install | run'
		@echo 'Prod:		make deploy | prod-update | prod-up | prod-down | prod-logs | prod-migrate | prod-ps'		