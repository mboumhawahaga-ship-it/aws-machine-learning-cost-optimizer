output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.cost_analyzer.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.cost_analyzer.arn
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket for reports"
  value       = aws_s3_bucket.cost_reports.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.cost_reports.arn
}
