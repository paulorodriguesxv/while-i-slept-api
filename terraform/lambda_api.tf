resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${local.resource_prefix}-api"
  retention_in_days = 14

  tags = local.common_tags
}

resource "aws_lambda_function" "api" {
  function_name = "${local.resource_prefix}-api"
  role          = aws_iam_role.api_lambda_role.arn
  runtime       = "python3.12"
  handler       = "handler.handler"
  timeout       = 15
  memory_size   = 512
  layers = var.use_lambda_layer ? [
    aws_lambda_layer_version.python_dependencies[0].arn,
  ] : []

  filename         = var.lambda_api_package_path
  source_code_hash = fileexists(var.lambda_api_package_path) ? filebase64sha256(var.lambda_api_package_path) : null

  environment {
    variables = {
      APP_ENV              = var.environment
      AWS_REGION           = var.aws_region
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
