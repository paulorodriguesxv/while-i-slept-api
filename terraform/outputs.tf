output "dynamodb_table_name" {
  description = "Name of the application DynamoDB table."
  value       = aws_dynamodb_table.app.name
}

output "dynamodb_table_arn" {
  description = "ARN of the application DynamoDB table."
  value       = aws_dynamodb_table.app.arn
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
