include makefiles/db.mk
include makefiles/docker.mk
include makefiles/app.mk

.PHONY: help

help:
		@echo 'DB:			make migrate m=... | update | downgrade | seed '
		@echo 'Docker:		make start | stop | reset'
		@echo 'App: 		make install | run'