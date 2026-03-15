variable "project_name" {
  description = "Project slug used in resource naming."
  type        = string
  default     = "while-i-slept-api"
}

variable "environment" {
  description = "Deployment environment (e.g. development, staging, production)."
  type        = string
  default     = "development"
}

variable "aws_region" {
  description = "AWS region for resources."
  type        = string
  default     = "us-east-1"
}

variable "use_localstack" {
  description = "Use LocalStack endpoints and local credentials instead of AWS."
  type        = bool
  default     = false
}

variable "dynamodb_billing_mode" {
  description = "DynamoDB billing mode for all application tables."
  type        = string
  default     = "PAY_PER_REQUEST"

  validation {
    condition     = var.dynamodb_billing_mode == "PAY_PER_REQUEST"
    error_message = "Only PAY_PER_REQUEST is supported in this Terraform foundation."
  }
}

variable "summary_queue_visibility_timeout_seconds" {
  description = "Visibility timeout for the summary jobs queue in seconds."
  type        = number
  default     = 60
}

variable "summary_queue_message_retention_seconds" {
  description = "Message retention period for the summary jobs queue in seconds."
  type        = number
  default     = 345600
}

variable "lambda_api_package_path" {
  description = "Path to the API Lambda deployment package zip."
  type        = string
  default     = "build/api_lambda.zip"
}

variable "lambda_ingestion_package_path" {
  description = "Path to the ingestion Lambda deployment package zip."
  type        = string
  default     = "build/ingestion_lambda.zip"
}

variable "lambda_worker_package_path" {
  description = "Path to the worker Lambda deployment package zip."
  type        = string
  default     = "build/worker_lambda.zip"
}

variable "ingestion_schedule_expression" {
  description = "EventBridge schedule expression for ingestion."
  type        = string
  default     = "rate(5 minutes)"
}
