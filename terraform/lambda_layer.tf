resource "aws_lambda_layer_version" "python_dependencies" {
  layer_name          = "${local.resource_prefix}-python-dependencies"
  filename            = var.lambda_python_dependencies_layer_path
  source_code_hash    = fileexists(var.lambda_python_dependencies_layer_path) ? filebase64sha256(var.lambda_python_dependencies_layer_path) : null
  compatible_runtimes = ["python3.12"]
}
