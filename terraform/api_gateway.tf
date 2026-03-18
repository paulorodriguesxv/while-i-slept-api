resource "aws_apigatewayv2_api" "api" {
  count = var.use_localstack ? 0 : 1

  name          = "${local.resource_prefix}-http-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "api_lambda" {
  count = var.use_localstack ? 0 : 1

  api_id                 = aws_apigatewayv2_api.api[0].id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
  timeout_milliseconds   = 30000
}

resource "aws_apigatewayv2_route" "default" {
  count = var.use_localstack ? 0 : 1

  api_id    = aws_apigatewayv2_api.api[0].id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.api_lambda[0].id}"
}

resource "aws_apigatewayv2_stage" "default" {
  count = var.use_localstack ? 0 : 1

  api_id      = aws_apigatewayv2_api.api[0].id
  name        = "$default"
  auto_deploy = true
}

resource "aws_api_gateway_rest_api" "api_local" {
  count = var.use_localstack ? 1 : 0

  name = "${local.resource_prefix}-rest-api"
}

resource "aws_api_gateway_resource" "proxy" {
  count = var.use_localstack ? 1 : 0

  rest_api_id = aws_api_gateway_rest_api.api_local[0].id
  parent_id   = aws_api_gateway_rest_api.api_local[0].root_resource_id
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_method" "root_any" {
  count = var.use_localstack ? 1 : 0

  rest_api_id   = aws_api_gateway_rest_api.api_local[0].id
  resource_id   = aws_api_gateway_rest_api.api_local[0].root_resource_id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "proxy_any" {
  count = var.use_localstack ? 1 : 0

  rest_api_id   = aws_api_gateway_rest_api.api_local[0].id
  resource_id   = aws_api_gateway_resource.proxy[0].id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "root_proxy" {
  count = var.use_localstack ? 1 : 0

  rest_api_id             = aws_api_gateway_rest_api.api_local[0].id
  resource_id             = aws_api_gateway_rest_api.api_local[0].root_resource_id
  http_method             = aws_api_gateway_method.root_any[0].http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api.invoke_arn
}

resource "aws_api_gateway_integration" "proxy_proxy" {
  count = var.use_localstack ? 1 : 0

  rest_api_id             = aws_api_gateway_rest_api.api_local[0].id
  resource_id             = aws_api_gateway_resource.proxy[0].id
  http_method             = aws_api_gateway_method.proxy_any[0].http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api.invoke_arn
}

resource "aws_api_gateway_deployment" "api_local" {
  count = var.use_localstack ? 1 : 0

  rest_api_id = aws_api_gateway_rest_api.api_local[0].id

  depends_on = [
    aws_api_gateway_integration.root_proxy,
    aws_api_gateway_integration.proxy_proxy,
  ]
}

resource "aws_api_gateway_stage" "default_local" {
  count = var.use_localstack ? 1 : 0

  rest_api_id   = aws_api_gateway_rest_api.api_local[0].id
  deployment_id = aws_api_gateway_deployment.api_local[0].id
  stage_name    = "default"
}

resource "aws_lambda_permission" "api_gateway_v2" {
  count = var.use_localstack ? 0 : 1

  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api[0].execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_v1" {
  count = var.use_localstack ? 1 : 0

  statement_id  = "AllowAPIGatewayInvokeLocal"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api_local[0].execution_arn}/*/*"
}
