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
          Subject  = "[ML Cost Optimizer] Approbation requise"
          Message  = "{% 
            '=== ML COST OPTIMIZER - RAPPORT HEBDOMADAIRE ===\n\n' &
            '💰 Coût total SageMaker : $' & $string($states.input.body.total_cost) & '\n' &
            '💸 Économies identifiées : $' & $string($states.input.body.potential_savings) & ' (' & $string($states.input.body.savings_pct) & '%)\n' &
            '📋 Recommandations : ' & $string($states.input.body.recommendation_count) & '\n\n' &
            '🔴 RESSOURCES IDLE À ARRÊTER :\n' &
            '  Notebooks : ' & $join($states.input.body.idle_resources.notebooks, ', ') & '\n' &
            '  Endpoints : ' & $join($states.input.body.idle_resources.endpoints, ', ') & '\n\n' &
            '✅ Pour APPROUVER les actions, répondez avec : approved\n' &
            '❌ Pour REFUSER, ignorez cet email (timeout 7 jours)\n\n' &
            '📄 Rapport complet : ' & $states.input.body.reports.markdown_url & '\n\n' &
            'Token (ne pas modifier) : ' & $states.context.Task.Token
          %}"
        }
        Next = "Action"
      }
      "Action" = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Output   = "{% $states.result.Payload %}"
        Arguments = {
          FunctionName = "${aws_lambda_function.cost_action.arn}:$LATEST"
          Payload = {
            approved       = "{% $states.input.approved %}"
            idle_resources = "{% $states.input.idle_resources %}"
          }
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
          TopicArn = "${aws_sns_topic.cost_analysis_notifications.arn}"
          Subject  = "[ML Cost Optimizer] Actions terminées"
          Message  = "{% 
            $states.input.body.approved = true ?
              '=== ML COST OPTIMIZER - ACTIONS EFFECTUÉES ===\n\n' &
              '✅ ' & $string($count($states.input.body.actions)) & ' action(s) exécutée(s) avec succès.\n\n' &
              $join($states.input.body.actions.resource & ' → ' & $states.input.body.actions.action & ' (' & $states.input.body.actions.status & ')', '\n')
            :
              '=== ML COST OPTIMIZER - ACTIONS REFUSÉES ===\n\nAucune ressource nà été modifiée.'
          %}"
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
