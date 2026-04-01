# EventBridge Rule - Trigger Lambda weekly on Monday at 8 UTC
resource "aws_cloudwatch_event_rule" "ml_cost_analysis_schedule" {
  name                = "${var.project_name}-schedule"
  description         = "Trigger ML cost analysis every Monday at 8:00 UTC"
  schedule_expression = "cron(0 8 ? * MON *)"

  tags = {
    Project   = var.project_name
    ManagedBy = "Terraform"
  }
}

# EventBridge Target - Lambda function
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.ml_cost_analysis_schedule.name
  target_id = "${var.project_name}-lambda-target"
  arn       = aws_lambda_function.cost_analyzer.arn

  depends_on = [aws_lambda_permission.allow_eventbridge]
}

# Lambda Permission - Allow EventBridge to invoke function
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cost_analyzer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ml_cost_analysis_schedule.arn
}
