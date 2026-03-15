data "aws_iam_policy_document" "api_lambda_assume_role" {
  statement {
    effect = "Allow"
    actions = [
      "sts:AssumeRole",
    ]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "api_lambda_role" {
  count = var.use_localstack ? 0 : 1

  name               = "${local.resource_prefix}-api-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.api_lambda_assume_role.json

  tags = local.common_tags
}

data "aws_iam_policy_document" "api_lambda_logs" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = [
      "arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/${local.resource_prefix}-api",
      "arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/${local.resource_prefix}-api:*",
    ]
  }
}

resource "aws_iam_policy" "api_lambda_logs" {
  count = var.use_localstack ? 0 : 1

  name   = "${local.resource_prefix}-api-lambda-logs"
  policy = data.aws_iam_policy_document.api_lambda_logs.json

  tags = local.common_tags
}

data "aws_iam_policy_document" "api_lambda_dynamodb" {
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:Query",
      "dynamodb:Scan",
    ]
    resources = [
      aws_dynamodb_table.articles.arn,
      aws_dynamodb_table.users.arn,
      "${aws_dynamodb_table.users.arn}/index/*",
      aws_dynamodb_table.devices.arn,
      aws_dynamodb_table.briefings.arn,
    ]
  }
}

resource "aws_iam_policy" "api_lambda_dynamodb" {
  count = var.use_localstack ? 0 : 1

  name   = "${local.resource_prefix}-api-lambda-dynamodb"
  policy = data.aws_iam_policy_document.api_lambda_dynamodb.json

  tags = local.common_tags
}

data "aws_iam_policy_document" "api_lambda_sqs" {
  statement {
    effect = "Allow"
    actions = [
      "sqs:SendMessage",
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
    ]
    resources = [
      aws_sqs_queue.summary_jobs.arn,
    ]
  }
}

resource "aws_iam_policy" "api_lambda_sqs" {
  count = var.use_localstack ? 0 : 1

  name   = "${local.resource_prefix}-api-lambda-sqs"
  policy = data.aws_iam_policy_document.api_lambda_sqs.json

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "api_lambda_logs" {
  count = var.use_localstack ? 0 : 1

  role       = aws_iam_role.api_lambda_role[0].name
  policy_arn = aws_iam_policy.api_lambda_logs[0].arn
}

resource "aws_iam_role_policy_attachment" "api_lambda_dynamodb" {
  count = var.use_localstack ? 0 : 1

  role       = aws_iam_role.api_lambda_role[0].name
  policy_arn = aws_iam_policy.api_lambda_dynamodb[0].arn
}

resource "aws_iam_role_policy_attachment" "api_lambda_sqs" {
  count = var.use_localstack ? 0 : 1

  role       = aws_iam_role.api_lambda_role[0].name
  policy_arn = aws_iam_policy.api_lambda_sqs[0].arn
}

data "aws_iam_policy_document" "ingestion_lambda_assume_role" {
  statement {
    effect = "Allow"
    actions = [
      "sts:AssumeRole",
    ]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ingestion_lambda_role" {
  count = var.use_localstack ? 0 : 1

  name               = "${local.resource_prefix}-ingestion-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.ingestion_lambda_assume_role.json

  tags = local.common_tags
}

data "aws_iam_policy_document" "ingestion_lambda_logs" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = [
      "arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/${local.resource_prefix}-ingestion",
      "arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/${local.resource_prefix}-ingestion:*",
    ]
  }
}

resource "aws_iam_policy" "ingestion_lambda_logs" {
  count = var.use_localstack ? 0 : 1

  name   = "${local.resource_prefix}-ingestion-lambda-logs"
  policy = data.aws_iam_policy_document.ingestion_lambda_logs.json

  tags = local.common_tags
}

data "aws_iam_policy_document" "ingestion_lambda_dynamodb" {
  statement {
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:Query",
      "dynamodb:Scan",
    ]
    resources = [
      aws_dynamodb_table.articles.arn,
    ]
  }
}

resource "aws_iam_policy" "ingestion_lambda_dynamodb" {
  count = var.use_localstack ? 0 : 1

  name   = "${local.resource_prefix}-ingestion-lambda-dynamodb"
  policy = data.aws_iam_policy_document.ingestion_lambda_dynamodb.json

  tags = local.common_tags
}

data "aws_iam_policy_document" "ingestion_lambda_sqs" {
  statement {
    effect = "Allow"
    actions = [
      "sqs:SendMessage",
    ]
    resources = [
      aws_sqs_queue.summary_jobs.arn,
    ]
  }
}

resource "aws_iam_policy" "ingestion_lambda_sqs" {
  count = var.use_localstack ? 0 : 1

  name   = "${local.resource_prefix}-ingestion-lambda-sqs"
  policy = data.aws_iam_policy_document.ingestion_lambda_sqs.json

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ingestion_lambda_logs" {
  count = var.use_localstack ? 0 : 1

  role       = aws_iam_role.ingestion_lambda_role[0].name
  policy_arn = aws_iam_policy.ingestion_lambda_logs[0].arn
}

resource "aws_iam_role_policy_attachment" "ingestion_lambda_dynamodb" {
  count = var.use_localstack ? 0 : 1

  role       = aws_iam_role.ingestion_lambda_role[0].name
  policy_arn = aws_iam_policy.ingestion_lambda_dynamodb[0].arn
}

resource "aws_iam_role_policy_attachment" "ingestion_lambda_sqs" {
  count = var.use_localstack ? 0 : 1

  role       = aws_iam_role.ingestion_lambda_role[0].name
  policy_arn = aws_iam_policy.ingestion_lambda_sqs[0].arn
}
