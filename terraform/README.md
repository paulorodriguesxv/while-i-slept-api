# Terraform Foundation

This folder contains the initial Terraform foundation for `while-i-slept-api`.

It provisions only the MVP base infrastructure:
- 4 DynamoDB tables aligned with the backend architecture
- 1 SQS queue for summary jobs
- 1 dead-letter queue (DLQ) for summary jobs
- 1 API Lambda function
- 1 worker Lambda function with SQS trigger
- 1 ingestion Lambda function
- 1 EventBridge schedule to trigger ingestion
- IAM role/policies for API Lambda (AWS mode)
- IAM role/policies for worker Lambda (AWS mode)
- IAM role/policies for ingestion Lambda (AWS mode)
- CloudWatch log groups for API, worker, and ingestion Lambdas

It intentionally does **not** include API Gateway resources yet.

## Files

- `versions.tf`: Terraform and provider version constraints
- `providers.tf`: provider configuration with AWS/LocalStack switching
- `variables.tf`: input variables
- `locals.tf`: common locals (naming + tags)
- `main.tf`: DynamoDB + SQS resources
- `iam.tf`: IAM roles and least-privilege policies for API, worker, and ingestion Lambdas
- `lambda_api.tf`: API Lambda function and CloudWatch log group
- `lambda_worker.tf`: worker Lambda function, CloudWatch log group, and SQS event source mapping
- `lambda_ingestion.tf`: ingestion Lambda function and CloudWatch log group
- `eventbridge.tf`: scheduled trigger for ingestion Lambda
- `outputs.tf`: useful output values
- `terraform.tfvars.example`: example variable values
- `local.tfvars`: ready-to-use LocalStack variable file
- `prod.tfvars.example`: production variable file example

## Naming

Resources are named with:

`<project_name>-<environment>-<resource>`

Example:
- `while-i-slept-api-development-articles`
- `while-i-slept-api-development-summary-jobs`

## Usage

1. Copy the example variables file:

```bash
cp terraform.tfvars.example terraform.tfvars
```

2. Initialize Terraform:

```bash
terraform init
```

3. Review the plan:

```bash
terraform plan
```

Or with explicit vars file:

```bash
terraform plan -var-file=terraform.tfvars
```

4. Apply:

```bash
terraform apply
```

Or with explicit vars file:

```bash
terraform apply -var-file=terraform.tfvars
```

## Running Terraform with LocalStack

1. Start LocalStack:

```bash
docker compose up localstack
```

2. Run Terraform against LocalStack:

```bash
cd terraform
terraform init
terraform apply -var-file=local.tfvars
```

When `use_localstack = true`, the provider points DynamoDB and SQS to:

`http://localhost:4566`

and uses local test credentials with AWS account checks disabled.

Lambda and EventBridge resources are also created in LocalStack mode to simulate the end-to-end AWS architecture locally.

If DynamoDB tables already exist in LocalStack, import each one before apply.

If Dynamodb present the error "Table already exists", maybe you will need to run the following command:

```bash
terraform import -var-file=local.tfvars aws_dynamodb_table.articles while-i-slept-local-articles
```

## Running Terraform on AWS

Create your production vars file from the example and apply:

```bash
cp prod.tfvars.example prod.tfvars
terraform init
terraform apply -var-file=prod.tfvars
```

When `use_localstack = false`, Terraform runs in normal AWS mode.

## API Lambda Infrastructure

The API Lambda runs the FastAPI backend with Python 3.12.

- Lambda function: `${project_name}-${environment}-api`
- Runtime: `python3.12`
- Handler: `run.sh`
- Timeout: `15s`
- Memory: `512 MB`

IAM permissions (least privilege) are split by concern:

- CloudWatch Logs:
  - `logs:CreateLogGroup`
  - `logs:CreateLogStream`
  - `logs:PutLogEvents`
- DynamoDB (scoped to the application tables: articles, users, devices, briefings):
  - `dynamodb:GetItem`
  - `dynamodb:PutItem`
  - `dynamodb:UpdateItem`
  - `dynamodb:Query`
  - `dynamodb:Scan`
  - includes access to users table indexes (`/index/*`) for GSI queries
- SQS (scoped to the summary queue):
  - `sqs:SendMessage`
  - `sqs:ReceiveMessage`
  - `sqs:DeleteMessage`
  - `sqs:GetQueueAttributes`

Lambda environment variables:

- `APP_ENV = var.environment`
- `ARTICLES_TABLE_NAME = aws_dynamodb_table.articles.name` (article ingestion and summary pipeline records)
- `USERS_TABLE_NAME = aws_dynamodb_table.users.name` (user profiles and preferences)
- `DEVICES_TABLE_NAME = aws_dynamodb_table.devices.name` (registered user devices)
- `BRIEFINGS_TABLE_NAME = aws_dynamodb_table.briefings.name` (generated briefing/feed entries)
- `SUMMARY_QUEUE_URL = aws_sqs_queue.summary_jobs.id`

In LocalStack mode, the API Lambda is created with the same resource name and local-compatible role ARN wiring.

## Scheduled Ingestion

EventBridge Scheduler runs the ingestion Lambda on a fixed interval.

Flow:
- EventBridge rule triggers ingestion Lambda (`rate(5 minutes)` by default)
- ingestion Lambda fetches RSS feeds
- ingestion writes raw articles to the articles DynamoDB table
- ingestion enqueues summary jobs into `summary-jobs` SQS

Ingestion Lambda configuration:
- Lambda function: `${project_name}-${environment}-ingestion`
- Runtime: `python3.12`
- Handler: `ingestion.handler`
- Timeout: `120s`
- Memory: `512 MB`

Ingestion Lambda IAM permissions (least privilege):
- CloudWatch Logs:
  - `logs:CreateLogGroup`
  - `logs:CreateLogStream`
  - `logs:PutLogEvents`
- DynamoDB (scoped to articles table):
  - `dynamodb:GetItem`
  - `dynamodb:PutItem`
  - `dynamodb:UpdateItem`
  - `dynamodb:Query`
  - `dynamodb:Scan`
- SQS (scoped to summary queue):
  - `sqs:SendMessage`

Ingestion Lambda environment variables:
- `APP_ENV = var.environment`
- `ARTICLES_TABLE_NAME = aws_dynamodb_table.articles.name`
- `SUMMARY_QUEUE_URL = aws_sqs_queue.summary_jobs.id`

In LocalStack mode, EventBridge and ingestion Lambda resources are created so scheduled ingestion can be exercised locally.

## Worker Lambda

The worker Lambda consumes summary jobs from SQS, generates summaries, and writes results into the briefings table.

Flow:
- SQS queue `summary-jobs` receives summary tasks
- Lambda event source mapping triggers worker in batches
- worker reads/writes required article and briefing records in DynamoDB

Worker Lambda configuration:
- Lambda function: `${project_name}-${environment}-worker`
- Runtime: `python3.12`
- Handler: `worker.handler`
- Timeout: `60s`
- Memory: `512 MB`
- SQS batch size: `5`

Worker Lambda IAM permissions (least privilege):
- CloudWatch Logs:
  - `logs:CreateLogGroup`
  - `logs:CreateLogStream`
  - `logs:PutLogEvents`
- DynamoDB (scoped to articles and briefings tables):
  - `dynamodb:GetItem`
  - `dynamodb:PutItem`
  - `dynamodb:UpdateItem`
  - `dynamodb:Query`
  - `dynamodb:Scan`
- SQS (scoped to summary queue):
  - `sqs:ReceiveMessage`
  - `sqs:DeleteMessage`
  - `sqs:GetQueueAttributes`

## Local Development Workflow

Start LocalStack:

```bash
docker compose up localstack
```

Deploy infrastructure:

```bash
cd terraform
terraform init
terraform apply -var-file=local.tfvars
```

Verify core resources:

```bash
awslocal lambda list-functions
awslocal events list-rules
awslocal sqs list-queues
```

## Destroying Infrastructure

To destroy resources created by Terraform, run from the `terraform/` directory and use the same vars file used during apply.

Destroy LocalStack environment:

```bash
terraform destroy -var-file=local.tfvars
```

Destroy AWS environment:

```bash
terraform destroy -var-file=prod.tfvars
```

## Resources Created In This Step

- `aws_dynamodb_table.articles`
  - stores raw ingested article and summary pipeline records
  - keys: `pk` (partition key), `sk` (sort key)
  - billing mode: `PAY_PER_REQUEST`
  - server-side encryption enabled

- `aws_dynamodb_table.users`
  - stores user profiles and preferences
  - keys: `user_id` (partition key), `sk` (sort key)
  - GSI: `GSI1` (`GSI1PK`, `GSI1SK`, projection `ALL`)
  - billing mode: `PAY_PER_REQUEST`
  - server-side encryption enabled

- `aws_dynamodb_table.devices`
  - stores registered user devices
  - keys: `user_id` (partition key), `sk` (sort key)
  - billing mode: `PAY_PER_REQUEST`
  - server-side encryption enabled

- `aws_dynamodb_table.briefings`
  - stores generated briefing/feed entries
  - keys: `pk` (partition key), `sk` (sort key)
  - billing mode: `PAY_PER_REQUEST`
  - server-side encryption enabled

- `aws_sqs_queue.summary_jobs`
  - configurable visibility timeout
  - configurable message retention
  - redrive policy to DLQ

- `aws_sqs_queue.summary_jobs_dlq`

- `aws_lambda_function.api`
- `aws_lambda_function.worker`
- `aws_lambda_function.ingestion`
- `aws_cloudwatch_log_group.api`
- `aws_cloudwatch_log_group.worker`
- `aws_cloudwatch_log_group.ingestion`
- `aws_lambda_event_source_mapping.worker_summary_jobs`
- `aws_cloudwatch_event_rule.ingestion_schedule`
- `aws_cloudwatch_event_target.ingestion_lambda`

## Tags

All resources include:
- `Project = var.project_name`
- `Environment = var.environment`
- `ManagedBy = "terraform"`
