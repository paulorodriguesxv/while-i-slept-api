resource "aws_dynamodb_table" "app" {
  name         = "${local.resource_prefix}-app"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "pk"
  range_key    = "sk"

  read_capacity  = var.dynamodb_billing_mode == "PROVISIONED" ? 5 : null
  write_capacity = var.dynamodb_billing_mode == "PROVISIONED" ? 5 : null

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }

  point_in_time_recovery {
    enabled = var.environment == "production"
  }

  tags = local.common_tags
}

resource "aws_sqs_queue" "summary_jobs_dlq" {
  name                      = "${local.resource_prefix}-summary-jobs-dlq"
  message_retention_seconds = var.summary_queue_message_retention_seconds

  tags = local.common_tags
}

resource "aws_sqs_queue" "summary_jobs" {
  name                       = "${local.resource_prefix}-summary-jobs"
  visibility_timeout_seconds = var.summary_queue_visibility_timeout_seconds
  message_retention_seconds  = var.summary_queue_message_retention_seconds

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.summary_jobs_dlq.arn
    maxReceiveCount     = 5
  })

  tags = local.common_tags
}
