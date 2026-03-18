output "dynamodb_table_name" {
  description = "Name of the primary articles DynamoDB table (backward-compatible output)."
  value       = aws_dynamodb_table.articles.name
}

output "dynamodb_table_arn" {
  description = "ARN of the primary articles DynamoDB table (backward-compatible output)."
  value       = aws_dynamodb_table.articles.arn
}

output "articles_table_name" {
  description = "Name of the articles DynamoDB table."
  value       = aws_dynamodb_table.articles.name
}

output "articles_table_arn" {
  description = "ARN of the articles DynamoDB table."
  value       = aws_dynamodb_table.articles.arn
}

output "users_table_name" {
  description = "Name of the users DynamoDB table."
  value       = aws_dynamodb_table.users.name
}

output "users_table_arn" {
  description = "ARN of the users DynamoDB table."
  value       = aws_dynamodb_table.users.arn
}

output "devices_table_name" {
  description = "Name of the devices DynamoDB table."
  value       = aws_dynamodb_table.devices.name
}

output "devices_table_arn" {
  description = "ARN of the devices DynamoDB table."
  value       = aws_dynamodb_table.devices.arn
}

output "briefings_table_name" {
  description = "Name of the briefings DynamoDB table."
  value       = aws_dynamodb_table.briefings.name
}

output "briefings_table_arn" {
  description = "ARN of the briefings DynamoDB table."
  value       = aws_dynamodb_table.briefings.arn
}

output "summary_queue_name" {
  description = "Name of the summary jobs SQS queue."
  value       = aws_sqs_queue.summary_jobs.name
}

output "summary_queue_url" {
  description = "URL of the summary jobs SQS queue."
  value       = aws_sqs_queue.summary_jobs.url
}

output "summary_queue_arn" {
  description = "ARN of the summary jobs SQS queue."
  value       = aws_sqs_queue.summary_jobs.arn
}

output "summary_dlq_url" {
  description = "URL of the summary jobs dead-letter queue."
  value       = aws_sqs_queue.summary_jobs_dlq.url
}

output "summary_dlq_arn" {
  description = "ARN of the summary jobs dead-letter queue."
  value       = aws_sqs_queue.summary_jobs_dlq.arn
}

output "api_lambda_function_name" {
  description = "API Lambda function name."
  value       = aws_lambda_function.api.function_name
}

output "api_lambda_role_arn" {
  description = "API Lambda IAM role ARN (null when use_localstack=true)."
  value       = var.use_localstack ? null : aws_iam_role.api_lambda_role[0].arn
}

output "ingestion_lambda_function_name" {
  description = "Ingestion Lambda function name."
  value       = aws_lambda_function.ingestion.function_name
}

output "eventbridge_rule_name" {
  description = "EventBridge ingestion schedule rule name."
  value       = aws_cloudwatch_event_rule.ingestion_schedule.name
}

output "worker_lambda_function_name" {
  description = "Worker Lambda function name."
  value       = aws_lambda_function.worker.function_name
}

output "worker_lambda_role_arn" {
  description = "Worker Lambda IAM role ARN (null when use_localstack=true)."
  value       = var.use_localstack ? null : aws_iam_role.worker_lambda_role[0].arn
}

output "python_dependencies_layer_arn" {
  description = "Shared Python dependencies Lambda Layer ARN."
  value       = aws_lambda_layer_version.python_dependencies.arn
}

output "api_endpoint" {
  description = "Public API endpoint for the FastAPI Lambda."
  value       = var.use_localstack ? aws_api_gateway_stage.default_local[0].invoke_url : aws_apigatewayv2_api.api[0].api_endpoint
}
