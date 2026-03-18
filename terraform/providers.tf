provider "aws" {
  region = var.aws_region

  access_key = var.use_localstack ? "test" : null
  secret_key = var.use_localstack ? "test" : null

  skip_credentials_validation = var.use_localstack
  skip_metadata_api_check     = var.use_localstack
  skip_requesting_account_id  = var.use_localstack

  dynamic "endpoints" {
    for_each = var.use_localstack ? [1] : []
    content {
      dynamodb = "http://localhost:4566"
      sqs      = "http://localhost:4566"
      eventbridge = "http://localhost:4566"
      lambda   = "http://localhost:4566"
      cloudwatch = "http://localhost:4566"
      cloudwatchlogs = "http://localhost:4566"
    }
  }
}
