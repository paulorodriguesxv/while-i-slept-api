# Terraform Foundation

This folder contains the initial Terraform foundation for `while-i-slept-api`.

It provisions only the MVP base infrastructure:
- 4 DynamoDB tables aligned with the backend architecture
- 1 SQS queue for summary jobs
- 1 dead-letter queue (DLQ) for summary jobs
- 1 API Lambda function (AWS-only)
- IAM role/policies for API Lambda (AWS-only)
- CloudWatch log group for API Lambda (AWS-only)

It intentionally does **not** include API Gateway or EventBridge resources yet.

## Files

- `versions.tf`: Terraform and provider version constraints
- `providers.tf`: provider configuration with AWS/LocalStack switching
- `variables.tf`: input variables
- `locals.tf`: common locals (naming + tags)
- `main.tf`: DynamoDB + SQS resources
- `iam.tf`: IAM role and least-privilege policies for API Lambda
- `lambda_api.tf`: API Lambda function and CloudWatch log group
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

If DynamoDB tables already exist in LocalStack, import each one before apply.

If Dynamodb present the error "Table already exists", maybe you will need to run the following command:

```bash
terraform import -var-file=local.tfvars aws_dynamodb_table.app  while-i-slept-local-app`
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

When `use_localstack = true`, Lambda/IAM/CloudWatch API resources are skipped (`count = 0`) to avoid LocalStack limitations and keep local plans/applies stable.

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

## Tags

All resources include:
- `Project = var.project_name`
- `Environment = var.environment`
- `ManagedBy = "terraform"`
