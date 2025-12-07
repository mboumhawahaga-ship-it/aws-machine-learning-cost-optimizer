terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Generer un ID unique pour eviter les conflits de noms
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# S3 Bucket pour stocker les rapports
resource "aws_s3_bucket" "cost_reports" {
  bucket = "${var.project_name}-reports-${random_id.bucket_suffix.hex}"

  tags = {
    Name        = "ML Cost Reports"
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}

# IAM Role pour Lambda
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Project   = var.project_name
    ManagedBy = "Terraform"
  }
}

# IAM Policy pour Lambda
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.project_name}-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ce:GetCostAndUsage",
          "ce:GetCostForecast"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl"
        ]
        Resource = "${aws_s3_bucket.cost_reports.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Lambda Function
resource "aws_lambda_function" "cost_analyzer" {
  filename         = "../lambda/function.zip"
  function_name    = "${var.project_name}-analyzer"
  role            = aws_iam_role.lambda_role.arn
  handler         = "main.handler"
  source_code_hash = filebase64sha256("../lambda/function.zip")
  runtime         = "python3.11"
  timeout         = 60
  memory_size     = 256

  environment {
    variables = {
      REPORT_BUCKET = aws_s3_bucket.cost_reports.id
      PROJECT_NAME  = var.project_name
    }
  }

  tags = {
    Project   = var.project_name
    ManagedBy = "Terraform"
  }
}

# CloudWatch Log Group pour Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.cost_analyzer.function_name}"
  retention_in_days = 7

  tags = {
    Project   = var.project_name
    ManagedBy = "Terraform"
  }
}
