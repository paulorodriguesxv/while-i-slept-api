# Terraform Foundation

This folder contains the initial Terraform foundation for `while-i-slept-api`.

It provisions only the MVP base infrastructure:
- 1 DynamoDB table (single-table design)
- 1 SQS queue for summary jobs
- 1 dead-letter queue (DLQ) for summary jobs

It intentionally does **not** include Lambda, EventBridge, or IAM resources yet.

## Files

- `versions.tf`: Terraform and provider version constraints
- `providers.tf`: AWS provider configuration
- `variables.tf`: input variables
- `locals.tf`: common locals (naming + tags)
- `main.tf`: DynamoDB + SQS resources
- `outputs.tf`: useful output values
- `terraform.tfvars.example`: example variable values

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
