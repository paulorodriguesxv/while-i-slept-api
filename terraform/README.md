# Terraform Foundation

This folder contains the initial Terraform foundation for `while-i-slept-api`.

It provisions only the MVP base infrastructure:
- 1 DynamoDB table (single-table design)
- 1 SQS queue for summary jobs
- 1 dead-letter queue (DLQ) for summary jobs

It intentionally does **not** include Lambda, EventBridge, or IAM resources yet.

## Files

- `versions.tf`: Terraform and provider version constraints
- `providers.tf`: provider configuration with AWS/LocalStack switching
- `variables.tf`: input variables
- `locals.tf`: common locals (naming + tags)
- `main.tf`: DynamoDB + SQS resources
- `outputs.tf`: useful output values
- `terraform.tfvars.example`: example variable values
- `local.tfvars`: ready-to-use LocalStack variable file
- `prod.tfvars.example`: production variable file example

## Naming

Resources are named with:

`<project_name>-<environment>-<resource>`

Example:
- `while-i-slept-api-development-app`
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

If dynamodb present the error "Table already exists", maybe you will need to run the following command:

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

- `aws_dynamodb_table.app`
  - `pk` (partition key), `sk` (sort key)
  - server-side encryption enabled
  - point-in-time recovery enabled only when `environment == "production"`

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
