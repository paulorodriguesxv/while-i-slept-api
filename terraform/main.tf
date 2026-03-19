resource "aws_dynamodb_table" "articles" {
  name         = "${local.resource_prefix}-articles"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "pk"
  range_key    = "sk"

  read_capacity  = var.dynamodb_billing_mode == "PROVISIONED" ? 5 : null
  write_capacity = var.dynamodb_billing_mode == "PROVISIONED" ? 5 : null

  point_in_time_recovery {
    enabled = var.environment == "production"
  }

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

  tags = local.common_tags
}

resource "aws_dynamodb_table" "users" {
  name         = "${local.resource_prefix}-users"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "user_id"
  range_key    = "sk"

  read_capacity  = var.dynamodb_billing_mode == "PROVISIONED" ? 5 : null
  write_capacity = var.dynamodb_billing_mode == "PROVISIONED" ? 5 : null

  point_in_time_recovery {
    enabled = var.environment == "production"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  attribute {
    name = "GSI1PK"
    type = "S"
  }

  attribute {
    name = "GSI1SK"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI1"
    projection_type = "ALL"

    key_schema {
      attribute_name = "GSI1PK"
      key_type       = "HASH"
    }

    key_schema {
      attribute_name = "GSI1SK"
      key_type       = "RANGE"
    }
  }

  server_side_encryption {
    enabled = true
  }

  tags = local.common_tags
}

resource "aws_dynamodb_table" "devices" {
  name         = "${local.resource_prefix}-devices"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "user_id"
  range_key    = "sk"

  read_capacity  = var.dynamodb_billing_mode == "PROVISIONED" ? 5 : null
  write_capacity = var.dynamodb_billing_mode == "PROVISIONED" ? 5 : null

  point_in_time_recovery {
    enabled = var.environment == "production"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }

  tags = local.common_tags
}

resource "aws_dynamodb_table" "briefings" {
  name         = "${local.resource_prefix}-briefings"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "pk"
  range_key    = "sk"

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
