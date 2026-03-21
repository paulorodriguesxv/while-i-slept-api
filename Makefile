.PHONY: help

GREEN  := $(shell tput -Txterm setaf 2)
WHITE  := $(shell tput -Txterm setaf 7)
BLUE   := $(shell tput -Txterm setaf 6)
RESET  := $(shell tput -Txterm sgr0)

# 2. A lógica Perl (escapando corretamente os cifrões do Perl com $$)
HELP_FUN = \
    %help; \
    while(<>) { \
        if (/^([a-zA-Z0-9\-_]+)\s*:.*\#\#(?:@([a-zA-Z0-9\-_]+))?\s(.*)$$/) { \
            push @{$$help{$$2 // 'Targets'}}, [$$1, $$3]; \
        } \
    }; \
    print "Usage: make [target]\n\n"; \
    foreach (sort keys %help) { \
        print "$(WHITE)$$_:$(RESET)\n"; \
        foreach (@{$$help{$$_}}) { \
            $$rep = " " x (30 - length $$_->[0]); \
            printf "  $(BLUE)%s$(RESET)%s$(GREEN)%s$(RESET)\n", $$_->[0], $$rep, $$_->[1]; \
        } \
        print "\n"; \
    }


.PHONY: help
help: ##@help Show this help message.
	@perl -e '$(HELP_FUN)' $(MAKEFILE_LIST)

.DEFAULT_GOAL := help

.PHONY: deploy-dev
deploy-dev: ##@infra Deploy AWS development environment with Terraform
	cd terraform && terraform init
	cd terraform && terraform apply -auto-approve -var-file=dev.tfvars

.PHONY: destroy-dev
destroy-dev: ##@infra Destroy AWS development environment with Terraform
	cd terraform && terraform init
	cd terraform && terraform destroy -auto-approve -var-file=dev.tfvars

.PHONY: test-ingestion
test-ingestion: ##@infra Invoke ingestion Lambda in AWS dev
	aws lambda invoke --function-name while-i-slept-dev-ingestion out.json


.PHONY: infra-up
infra-up: ##@infra-up [Deprecated] Start LocalStack
	docker compose up -d localstack

.PHONY: infra-down
infra-down: ##@infra-down [Deprecated] Stop and remove LocalStack
	docker compose stop localstack
	docker compose rm -f localstack

.PHONY: migrate
migrate: ##@migrate Run database migrations
migrate: infra-up 
	docker compose run --rm api python scripts/create_tables.py

.PHONY: up
up: ##@up Start the API and local infrastructure
up:	infra-up \
	migrate
	docker compose up -d api

.PHONY: down
down: ##@down Stop and remove all containers
	docker compose down --remove-orphans

.PHONY: logs
logs: ##@logs Tail logs for local services
	docker compose logs -f api localstack

.PHONY: test
test: ##@test Run tests with coverage
test: infra-up
	docker compose build tests
	docker compose run --rm tests

.PHONY: coverage
coverage: ##@coverage Run tests with coverage
coverage: infra-up
	docker compose build tests
	docker compose run --rm tests sh -lc "python scripts/create_tables.py && pytest -q --cov=while_i_slept_api.services --cov=while_i_slept_api.repositories.memory --cov=while_i_slept_api.article_pipeline --cov-report=term-missing --cov-report=html:htmlcov"

.PHONY: shell
shell: ##@shell Open a shell in the API container
	docker compose exec api /bin/sh

.PHONY: create-queues
create-queues: ##@create-queues Create SQS queues (summary + article jobs)
	docker compose run --rm api sh -lc "python scripts/create_queues.py && SQS_QUEUE_NAME=article-jobs python scripts/create_queues.py"

.PHONY: create-table
create-table: ##@create-table Create DynamoDB table
	docker compose run --rm api sh -lc "python scripts/create_table.py"

.PHONY: local-worker
local-worker: ##@local-worker Run local summary worker
	docker compose run --rm api sh -lc "python -m while_i_slept_api.article_pipeline.local_consumer"

.PHONY: local-ingestion
local-ingestion: ##@local-ingestion Enqueue article jobs from RSS feeds
	docker compose run --rm api sh -lc "python -c 'from while_i_slept_api.article_pipeline.ingestion_handler import lambda_handler; print(lambda_handler(None, None))'"

.PHONY: local-fetch
local-fetch: ##@local-fetch [Deprecated] Alias for local-ingestion
	make local-ingestion

.PHONY: local-article-processor
local-article-processor: ##@local-article-processor Run local article-job processor
	docker compose run --rm api sh -lc "python -m while_i_slept_api.article_pipeline.article_job_local_consumer"

.PHONY: local-article-processor-once
local-article-processor-once: ##@local-article-processor-once Run local article-job processor in finite once mode
	docker compose run --rm api sh -lc "python -m while_i_slept_api.article_pipeline.article_job_local_consumer --once"

.PHONY: purge-queue
purge-queue: ##@purge-queue Purge SQS queue
	PYTHONPATH=src python scripts/purge_queue.py

.PHONY: base-image
base-image: ##@base-image Build base Docker images
	docker compose build $(if $(NO_CACHE),--no-cache --pull,) api tests

.PHONY: summary-pipeline-run
summary-pipeline-run: ##@summary-pipeline-run Run the entire summary pipeline (init, ingestion, article processor, worker)
summary-pipeline-run: \
	summary-pipeline-init \
	summary-pipeline-ingestion \
	summary-pipeline-article-processor \
	summary-pipeline-worker \
	

.PHONY: summary-pipeline-init
summary-pipeline-init: ##@summary-pipeline-init Initialize the summary pipeline
summary-pipeline-init: infra-up \
	create-table \
	create-queues

.PHONY: summary-pipeline-fetch
summary-pipeline-fetch: ##@summary-pipeline-fetch [Deprecated] Alias for summary-pipeline-ingestion
	make summary-pipeline-ingestion

.PHONY: summary-pipeline-ingestion
summary-pipeline-ingestion: ##@summary-pipeline-ingestion Enqueue article jobs for the summary pipeline
	make local-ingestion

.PHONY: summary-pipeline-article-processor
summary-pipeline-article-processor: ##@summary-pipeline-article-processor Process queued article jobs once
	make local-article-processor-once

# .PHONY: summary-pipeline-worker
# summary-pipeline-worker: ##@summary-pipeline-worker Run the local worker for the summary pipeline
# 	make local-worker

.PHONY: summary-worker-loop
summary-worker-loop: ##@summary-worker-loop Continuously run the local worker for testing
	docker compose run --rm api sh -lc "while true; do make local-worker; sleep 2; done"

.PHONY: article-processor-loop
article-processor-loop: ##@article-processor-loop Continuously run local article processor for testing
	docker compose run --rm api sh -lc "while true; do make local-article-processor-once; sleep 2; done"

.PHONY: inspect-db
inspect-db: ##@inspect-db Inspect the contents of the DynamoDB table
	aws dynamodb scan --table-name $${TABLE_NAME:-while-i-slept-dev-articles}

.PHONY: clean-dynamo-tables
clean-dynamo-tables: ##@clean-dynamo-tables Remove all local DynamoDB tables and recreate app tables
clean-dynamo-tables: infra-up
	docker compose run --rm api sh -lc "python scripts/clean_dynamo_tables.py"
	docker compose run --rm api sh -lc "python scripts/create_tables.py"
	docker compose run --rm api sh -lc "python scripts/create_table.py"

.PHONY: local-worker-once
local-worker-once: ##@local-worker-once Run local summary worker in finite once mode
	docker compose run --rm api sh -lc "python -m while_i_slept_api.article_pipeline.local_consumer --once"

.PHONY: summary-pipeline-worker
summary-pipeline-worker: ##@summary-pipeline-worker Run the local worker for the summary pipeline in once mode
	make local-worker-once

.PHONY: build-layer
build-layer: ##@build Build shared Lambda layer dependencies package
	docker compose run --rm --user $$(id -u):$$(id -g) lambda-builder bash scripts/build_layer.sh

.PHONY: build-api
build-api: ##@build Build API Lambda package
	docker compose run --rm --user $$(id -u):$$(id -g) lambda-builder bash scripts/build_lambda.sh api

.PHONY: build-worker
build-worker: ##@build Build worker Lambda package
	docker compose run --rm --user $$(id -u):$$(id -g) lambda-builder bash scripts/build_lambda.sh worker

.PHONY: build-ingestion
build-ingestion: ##@build Build ingestion Lambda package
	docker compose run --rm --user $$(id -u):$$(id -g) lambda-builder bash scripts/build_lambda.sh ingestion

.PHONY: build-article-processor
build-article-processor: ##@build Build article processor Lambda package
	docker compose run --rm --user $$(id -u):$$(id -g) lambda-builder bash scripts/build_lambda.sh article_processor

.PHONY: build-lambdas
build-lambdas: ##@build Build all Lambda function packages
build-lambdas: build-api build-worker build-ingestion build-article-processor

.PHONY: build
build: ##@build Build shared layer and all Lambda packages
build: build-layer build-lambdas

.PHONY: build-local
build-local: ##@build [Deprecated] Build Lambda packages with embedded dependencies (LocalStack mode)
	docker compose run --rm --user $$(id -u):$$(id -g) -e USE_LAMBDA_LAYER=false lambda-builder bash scripts/build_lambda.sh api
	docker compose run --rm --user $$(id -u):$$(id -g) -e USE_LAMBDA_LAYER=false lambda-builder bash scripts/build_lambda.sh worker
	docker compose run --rm --user $$(id -u):$$(id -g) -e USE_LAMBDA_LAYER=false lambda-builder bash scripts/build_lambda.sh ingestion
	docker compose run --rm --user $$(id -u):$$(id -g) -e USE_LAMBDA_LAYER=false lambda-builder bash scripts/build_lambda.sh article_processor

.PHONY: clean-build
clean-build: ##@build Remove generated Lambda build artifacts
	docker compose run --rm lambda-builder bash -lc "rm -rf /app/build"
