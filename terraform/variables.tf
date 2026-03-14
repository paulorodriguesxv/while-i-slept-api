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

variable "dynamodb_billing_mode" {
  description = "DynamoDB billing mode. PAY_PER_REQUEST is recommended for MVP usage."
  type        = string
  default     = "PAY_PER_REQUEST"

  validation {
    condition     = contains(["PAY_PER_REQUEST", "PROVISIONED"], var.dynamodb_billing_mode)
    error_message = "dynamodb_billing_mode must be PAY_PER_REQUEST or PROVISIONED."
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
