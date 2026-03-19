resource "aws_cloudwatch_log_group" "worker" {
  name              = "/aws/lambda/${local.resource_prefix}-worker"
  retention_in_days = 14

  tags = local.common_tags
}

resource "aws_lambda_function" "worker" {
  function_name = "${local.resource_prefix}-worker"
  role          = var.use_localstack ? "arn:aws:iam::000000000000:role/${local.resource_prefix}-worker-lambda-role" : aws_iam_role.worker_lambda_role[0].arn
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
    variables = {
      APP_ENV              = var.environment
      ARTICLES_TABLE_NAME  = aws_dynamodb_table.articles.name
      BRIEFINGS_TABLE_NAME = aws_dynamodb_table.briefings.name
      SUMMARY_QUEUE_URL    = aws_sqs_queue.summary_jobs.id
    }
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
