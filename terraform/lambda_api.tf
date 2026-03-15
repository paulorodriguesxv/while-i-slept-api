resource "aws_cloudwatch_log_group" "api" {
  count = var.use_localstack ? 0 : 1

  name              = "/aws/lambda/${local.resource_prefix}-api"
  retention_in_days = 14

  tags = local.common_tags
}

resource "aws_lambda_function" "api" {
  count = var.use_localstack ? 0 : 1

  function_name = "${local.resource_prefix}-api"
  role          = aws_iam_role.api_lambda_role[0].arn
  runtime       = "python3.12"
  handler       = "run.sh"
  timeout       = 15
  memory_size   = 512

  filename         = var.lambda_api_package_path
  source_code_hash = fileexists(var.lambda_api_package_path) ? filebase64sha256(var.lambda_api_package_path) : null

  environment {
    variables = {
      APP_ENV              = var.environment
      ARTICLES_TABLE_NAME  = aws_dynamodb_table.articles.name
      USERS_TABLE_NAME     = aws_dynamodb_table.users.name
      DEVICES_TABLE_NAME   = aws_dynamodb_table.devices.name
      BRIEFINGS_TABLE_NAME = aws_dynamodb_table.briefings.name
      SUMMARY_QUEUE_URL    = aws_sqs_queue.summary_jobs.id
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.api,
    aws_iam_role_policy_attachment.api_lambda_logs,
    aws_iam_role_policy_attachment.api_lambda_dynamodb,
    aws_iam_role_policy_attachment.api_lambda_sqs,
  ]

  tags = local.common_tags
}
