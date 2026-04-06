resource "aws_sfn_state_machine" "ml_cost_optimizer_workflow" {
  name     = "ml-cost-optimizer-workflow"
  role_arn = aws_iam_role.lambda_role.arn
  type     = "STANDARD"

  definition = jsonencode({
    Comment     = "ml-cost-optimizer-analyzer"
    StartAt     = "Scan-SageMaker"
    QueryLanguage = "JSONata"
    States = {
      "Scan-SageMaker" = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Output   = "{% $states.result.Payload %}"
        Arguments = {
          FunctionName = "arn:aws:lambda:eu-west-1:384621379481:function:ml-cost-optimizer-analyzer:$LATEST"
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
        Next = "Analyse-Rapport"
      }
      "Analyse-Rapport" = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Output   = "{% $states.result.Payload %}"
        Arguments = {
          FunctionName = "arn:aws:lambda:eu-west-1:384621379481:function:ml-cost-optimizer-analyzer:$LATEST"
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
        Next = "Action"
      }
      "Action" = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Output   = "{% $states.result.Payload %}"
        Arguments = {
          FunctionName = "arn:aws:lambda:eu-west-1:384621379481:function:ml-cost-optimizer-action:$LATEST"
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
          TopicArn = "arn:aws:sns:eu-west-1:384621379481:ml-cost-optimizer-notifications"
        }
        End = true
      }
    }
  })

  tags = {
    Project   = "ml-cost-optimizer"
    ManagedBy = "Terraform"
  }
}
