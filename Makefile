.PHONY: infra-up infra-down migrate up down logs test coverage shell

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
	docker compose build tests
	docker compose run --rm tests

coverage: infra-up
	docker compose build tests
	docker compose run --rm tests sh -lc "python scripts/create_tables.py && pytest -q --cov=while_i_slept_api.services --cov=while_i_slept_api.repositories.memory --cov=while_i_slept_api.article_pipeline --cov=while_i_slept_api.summarizer_worker --cov-report=term-missing --cov-report=html:htmlcov"

shell:
	docker compose exec api /bin/sh

create-queues:
	docker compose run --rm api sh -lc "python scripts/create_queues.py"


create-table:
	docker compose run --rm api sh -lc "python scripts/create_table.py"

local-worker:
	docker compose run --rm api sh -lc "python -m while_i_slept_api.summarizer_worker.local_consumer"

local-fetch:
	docker compose run --rm api sh -lc "python scripts/fetch_rss.py"

purge-queue:
	PYTHONPATH=src python scripts/purge_queue.py

.PHONY: base-image

base-image:
	docker compose build $(if $(NO_CACHE),--no-cache --pull,) api tests
