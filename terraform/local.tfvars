project_name = "while-i-slept"
environment  = "local"
aws_region   = "us-east-1"

use_localstack        = true
dynamodb_billing_mode = "PAY_PER_REQUEST"

summary_queue_visibility_timeout_seconds = 30
summary_queue_message_retention_seconds  = 1209600
