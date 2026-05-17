include makefiles/db.mk
include makefiles/docker.mk
include makefiles/app.mk

.PHONY: help

help:
		@echo 'DB:			make db | migrate m=... | update | downgrade | seed | setup'
		@echo 'Docker:		make start | stop | reset'
		@echo 'App': 		make install | run