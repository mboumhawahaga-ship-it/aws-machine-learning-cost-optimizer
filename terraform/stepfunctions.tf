resource "aws_sfn_state_machine" "ml_cost_optimizer_workflow" {
  name     = "${var.project_name}-workflow"
  role_arn = aws_iam_role.sfn_role.arn
  type     = "STANDARD"

  definition = jsonencode({
    Comment       = "ml-cost-optimizer-analyzer"
    StartAt       = "Scan-SageMaker"
    QueryLanguage = "JSONata"
    States = {
      "Scan-SageMaker" = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Output   = "{% $states.result.Payload %}"
        Arguments = {
          FunctionName = "${aws_lambda_function.cost_analyzer.arn}:$LATEST"
          Payload      = "{% $states.input %}"
        }
        Retry = [
          {
            ErrorEquals = [
              "Lambda.ServiceException",
              "Lambda.AWSLambdaException",
              "Lambda.SdkClientException",
              "Lambda.TooManyRequestsException"
            ]
            IntervalSeconds = 1
            MaxAttempts     = 3
            BackoffRate     = 2
            JitterStrategy  = "FULL"
          }
        ]
        Next = "Attente-Approbation"
      }
      "Attente-Approbation" = {
        Type     = "Task"
        Resource = "arn:aws:states:::sns:publish.waitForTaskToken"
        Arguments = {
          TopicArn = "${aws_sns_topic.cost_analysis_notifications.arn}"
          Message  = "{% 'Rapport ML Cost disponible. Approuvez les actions : ' & $states.taskToken %}"
        }
        Next = "Action"
      }
      "Action" = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Output   = "{% $states.result.Payload %}"
        Arguments = {
          FunctionName = "${aws_lambda_function.cost_action.arn}:$LATEST"
          Payload      = "{% $states.input %}"
        }
        Retry = [
          {
            ErrorEquals = [
              "Lambda.ServiceException",
              "Lambda.AWSLambdaException",
              "Lambda.SdkClientException",
              "Lambda.TooManyRequestsException"
            ]
            IntervalSeconds = 1
            MaxAttempts     = 3
            BackoffRate     = 2
            JitterStrategy  = "FULL"
          }
        ]
        Next = "Notification"
      }
      "Notification" = {
        Type     = "Task"
        Resource = "arn:aws:states:::sns:publish"
        Arguments = {
          Message  = "{% $states.input %}"
          TopicArn = "${aws_sns_topic.cost_analysis_notifications.arn}"
        }
        End = true
      }
    }
  })

  tags = {
    Project   = var.project_name
    ManagedBy = "Terraform"
  }
}
