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

output "article_jobs_queue_name" {
  description = "Name of the article jobs SQS queue."
  value       = aws_sqs_queue.article_jobs.name
}

output "article_jobs_queue_url" {
  description = "URL of the article jobs SQS queue."
  value       = aws_sqs_queue.article_jobs.url
}

output "article_jobs_queue_arn" {
  description = "ARN of the article jobs SQS queue."
  value       = aws_sqs_queue.article_jobs.arn
}

output "api_lambda_function_name" {
  description = "API Lambda function name."
  value       = aws_lambda_function.api.function_name
}

output "api_lambda_role_arn" {
  description = "API Lambda IAM role ARN."
  value       = aws_iam_role.api_lambda_role.arn
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
  description = "Worker Lambda IAM role ARN."
  value       = aws_iam_role.worker_lambda_role.arn
}

output "article_processor_lambda_function_name" {
  description = "Article processor Lambda function name."
  value       = aws_lambda_function.article_processor.function_name
}

output "article_processor_lambda_role_arn" {
  description = "Article processor Lambda IAM role ARN."
  value       = aws_iam_role.article_processor_lambda_role.arn
}

output "python_dependencies_layer_arn" {
  description = "Shared Python dependencies Lambda Layer ARN (null when use_lambda_layer=false)."
  value       = var.use_lambda_layer ? aws_lambda_layer_version.python_dependencies[0].arn : null
}

output "api_endpoint" {
  description = "Public API endpoint for the FastAPI Lambda."
  value       = aws_apigatewayv2_api.api.api_endpoint
}
