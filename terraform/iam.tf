# IAM Role dédié pour Step Functions
resource "aws_iam_role" "sfn_role" {
  name = "${var.project_name}-sfn-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Project   = var.project_name
    ManagedBy = "Terraform"
  }
}

# IAM Policy pour Step Functions - invoke Lambda + publish SNS
resource "aws_iam_role_policy" "sfn_policy" {
  name = "${var.project_name}-sfn-policy"
  role = aws_iam_role.sfn_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "InvokeLambda"
        Effect = "Allow"
        Action = ["lambda:InvokeFunction"]
        Resource = [
          aws_lambda_function.cost_analyzer.arn,
          aws_lambda_function.cost_action.arn
        ]
      },
      {
        Sid      = "PublishSNS"
        Effect   = "Allow"
        Action   = ["sns:Publish"]
        Resource = aws_sns_topic.cost_analysis_notifications.arn
      }
    ]
  })
}

# IAM Policy pour Lambda - Least Privilege
resource "aws_iam_role_policy" "lambda_sagemaker_policy" {
  name = "${var.project_name}-lambda-sagemaker-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SageMakerReadOnly"
        Effect = "Allow"
        Action = [
          "sagemaker:ListNotebookInstances",
          "sagemaker:ListTrainingJobs",
          "sagemaker:ListEndpoints",
          "sagemaker:DescribeNotebookInstance",
          "sagemaker:ListTags",
          "sagemaker:StopNotebookInstance",
          "sagemaker:DeleteEndpoint"
        ]
        Resource = "*"
      },
      {
        Sid    = "CloudWatchMetricsReadOnly"
        Effect = "Allow"
        Action = [
          "cloudwatch:GetMetricStatistics"
        ]
        Resource = "*"
      },
      {
        Sid    = "CostExplorerReadOnly"
        Effect = "Allow"
        Action = [
          "ce:GetCostAndUsage",
          "ce:GetCostForecast"
        ]
        Resource = "*"
      },
      {
        Sid    = "PricingReadOnly"
        Effect = "Allow"
        Action = [
          "pricing:GetProducts"
        ]
        Resource = "*"
      },
      {
        Sid    = "S3BucketWriteOnly"
        Effect = "Allow"
        Action = [
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.cost_reports.arn}/*"
      },
      {
        Sid    = "SNSPublish"
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.cost_analysis_notifications.arn
      }
    ]
  })
}
