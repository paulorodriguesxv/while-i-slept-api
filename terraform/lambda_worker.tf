resource "aws_cloudwatch_log_group" "worker" {
  name              = "/aws/lambda/${local.resource_prefix}-worker"
  retention_in_days = 14

  tags = local.common_tags
}

resource "aws_lambda_function" "worker" {
  function_name = "${local.resource_prefix}-worker"
  role          = aws_iam_role.worker_lambda_role.arn
  runtime       = "python3.12"
  handler       = "handler.handler"
  timeout       = 60
  memory_size   = 512
  layers = var.use_lambda_layer ? [
    aws_lambda_layer_version.python_dependencies[0].arn,
  ] : []

  filename         = var.lambda_worker_package_path
  source_code_hash = fileexists(var.lambda_worker_package_path) ? filebase64sha256(var.lambda_worker_package_path) : null

  environment {
    variables = merge(
      {
        APP_ENV                     = var.environment
        APP_AWS_REGION              = var.aws_region
        APP_ARTICLES_TABLE          = aws_dynamodb_table.articles.name
        APP_USERS_TABLE             = aws_dynamodb_table.users.name
        APP_DEVICES_TABLE           = aws_dynamodb_table.devices.name
        APP_BRIEFINGS_TABLE         = aws_dynamodb_table.briefings.name
        APP_SUMMARY_JOBS_QUEUE_NAME = aws_sqs_queue.summary_jobs.name
        APP_SUMMARY_JOBS_QUEUE_URL  = aws_sqs_queue.summary_jobs.id
        APP_SUMMARIZER_IMPL         = "smart"
      },
      var.aws_endpoint_url == null ? {} : {
        APP_AWS_ENDPOINT_URL = var.aws_endpoint_url
      },
    )
  }

  depends_on = [
    aws_cloudwatch_log_group.worker,
    aws_iam_role_policy_attachment.worker_lambda_logs,
    aws_iam_role_policy_attachment.worker_lambda_dynamodb,
    aws_iam_role_policy_attachment.worker_lambda_sqs,
  ]

  tags = local.common_tags
}

resource "aws_lambda_event_source_mapping" "worker_summary_jobs" {
  event_source_arn = aws_sqs_queue.summary_jobs.arn
  function_name    = aws_lambda_function.worker.arn
  batch_size       = 5
  enabled          = true
}
