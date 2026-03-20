# Terraform Foundation

This folder provisions the AWS infrastructure for `while-i-slept`.

## AWS Development Environment

Deploy the isolated development stack:

```bash
terraform init
terraform apply -var-file=dev.tfvars
```

Or from repository root:

```bash
make deploy-dev
```

Destroy it with:

```bash
make destroy-dev
```

## Variables

- `environment` (default: `dev`)
- `aws_region` (default: `us-east-1`)
- `use_lambda_layer` (default: `true`)

`dev.tfvars` sets:

```hcl
environment      = "dev"
use_lambda_layer = true
```

## Naming Convention

All resources are environment-scoped with this prefix:

`<project_name>-<environment>`

With defaults, resources are named like:

- `while-i-slept-dev-articles`
- `while-i-slept-dev-summary-jobs`
- `while-i-slept-dev-api`
- `while-i-slept-dev-ingestion-schedule`

## Resources

- DynamoDB tables: `articles`, `users`, `devices`, `briefings`
- SQS queue + DLQ for summary jobs
- API Lambda, ingestion Lambda, worker Lambda
- EventBridge scheduled ingestion rule + target
- API Gateway HTTP API
- IAM roles/policies for each Lambda
- CloudWatch log groups
- Optional shared Lambda dependencies layer

## Lambda Environment Variables

Each Lambda receives:

- `ARTICLES_TABLE_NAME`
- `BRIEFINGS_TABLE_NAME`
- `DEVICES_TABLE_NAME`
- `USERS_TABLE_NAME`
- `SUMMARY_QUEUE_URL`
- `APP_ENV`
- `AWS_REGION`
