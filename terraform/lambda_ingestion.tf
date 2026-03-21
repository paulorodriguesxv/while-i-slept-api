resource "aws_cloudwatch_log_group" "ingestion" {
  name              = "/aws/lambda/${local.resource_prefix}-ingestion"
  retention_in_days = 14

  tags = local.common_tags
}

resource "aws_lambda_function" "ingestion" {
  function_name = "${local.resource_prefix}-ingestion"
  role          = aws_iam_role.ingestion_lambda_role.arn
  runtime       = "python3.12"
  handler       = "handler.handler"
  timeout       = 120
  memory_size   = 512
  layers = var.use_lambda_layer ? [
    aws_lambda_layer_version.python_dependencies[0].arn,
  ] : []

  filename         = var.lambda_ingestion_package_path
  source_code_hash = fileexists(var.lambda_ingestion_package_path) ? filebase64sha256(var.lambda_ingestion_package_path) : null

  environment {
    variables = merge(
      {
        APP_ENV                     = var.environment
        APP_AWS_REGION              = var.aws_region
        APP_FEED_LANGUAGE           = "pt"
        APP_FEED_TOPIC              = "world"
        APP_ARTICLE_JOBS_QUEUE_NAME = aws_sqs_queue.article_jobs.name
        APP_ARTICLE_JOBS_QUEUE_URL  = aws_sqs_queue.article_jobs.id
      },
      var.aws_endpoint_url == null ? {} : {
        APP_AWS_ENDPOINT_URL = var.aws_endpoint_url
      },
    )
  }

  depends_on = [
    aws_cloudwatch_log_group.ingestion,
    aws_iam_role_policy_attachment.ingestion_lambda_logs,
    aws_iam_role_policy_attachment.ingestion_lambda_sqs,
  ]

  tags = local.common_tags
}
