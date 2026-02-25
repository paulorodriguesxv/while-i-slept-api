.PHONY: infra-up infra-down migrate up down logs test shell

infra-up:
	docker compose up -d localstack

infra-down:
	docker compose stop localstack
	docker compose rm -f localstack

migrate: infra-up
	docker compose run --rm api python scripts/create_tables.py

up: infra-up migrate
	docker compose up -d api

down:
	docker compose down --remove-orphans

logs:
	docker compose logs -f api localstack

test: infra-up
	docker compose run --rm tests

shell:
	docker compose exec api /bin/sh
