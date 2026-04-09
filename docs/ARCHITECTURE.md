# Architecture — AWS ML Cost Optimizer

This project automatically scans SageMaker resources, analyzes costs, and takes
optimization actions (with human approval). Everything runs serverless on AWS.

---

## How it works — big picture

```
EventBridge (weekly cron — every Monday 8:00 UTC)
        |
        v
 Step Functions Workflow
        |
        |---> [1] Scan-SageMaker        (Lambda: ml-cost-optimizer-analyzer)
        |           Scans all SageMaker resources + fetches real costs
        |           Saves JSON + Markdown reports to S3
        |
        |---> [2] Attente-Approbation   (SNS waitForTaskToken)
        |           Sends report to team — workflow pauses
        |           Resumes only when a human sends back the task token
        |
        |---> [3] Action                (Lambda: ml-cost-optimizer-action)
        |           Executes the approved action (stop notebook / delete endpoint)
        |
        |---> [4] Notification          (SNS)
                    Sends final confirmation email to subscribers
```

---

## Lambda files

### `lambda/discovery.py`
Scans all live SageMaker resources via boto3 with full pagination:
- `scan_notebooks()` — lists all notebook instances with status, instance type, hourly price (live from Pricing API), and carbon footprint estimate
- `scan_endpoints()` — lists all endpoints with status
- `scan_training_jobs()` — lists all completed training jobs
- `check_rgpd_compliance()` — checks GDPR tags (`owner`, `data-classification`, `expiration-date`) on each resource using correct ARN format via STS
- `calculate_carbon_footprint()` — estimates CO2 in kg/month based on instance type
- `run_discovery()` — orchestrates all scans and returns a single report dict including GDPR compliance summary

### `lambda/main.py`
Main analysis Lambda — entry point for step 1 in the workflow:
- `get_real_costs()` — queries AWS Cost Explorer for real SageMaker spend this month. Handles the 24h activation delay gracefully with clear warning messages. Falls back to mock data on error or empty results
- `generate_recommendations()` — produces a prioritized list of savings opportunities (notebooks, training, endpoints, storage) sorted by ROI
- `generate_markdown_report()` / `save_markdown_report()` — builds and uploads a Markdown report to S3
- `save_json_report()` — uploads a structured JSON report to S3 with strict schema
- `send_sns_notification()` — sends a savings summary via SNS (non-blocking)
- `handler()` — Lambda entry point: orchestrates the full analysis flow

### `lambda/action.py`
Executes a single action on a SageMaker resource. **Only runs after explicit human approval via task token.**
- `stop_notebook(name)` — stops a notebook instance (no deletion)
- `delete_endpoint(name)` — deletes an inactive endpoint
- `handler(event)` — reads `action_type` and `resource_name` from the event, routes to the right function

---

## Step Functions workflow

| Step | State | Resource | What happens |
|------|-------|----------|--------------|
| 1 | Scan-SageMaker | Lambda: analyzer | Scans resources, fetches costs, saves reports to S3 |
| 2 | Attente-Approbation | SNS waitForTaskToken | Pauses workflow — resumes only after human approval |
| 3 | Action | Lambda: action | Executes the approved action (stop/delete) |
| 4 | Notification | SNS direct | Sends final confirmation to subscribers |

Each Lambda step retries up to 3 times with exponential backoff + full jitter on AWS transient errors.
The workflow uses **JSONata** for state I/O transformations.

---

## AWS services used

| Service | Why |
|---------|-----|
| **Lambda** | Serverless compute — no infrastructure to manage |
| **Step Functions** | Orchestrates the multi-step workflow with retries, state, and human approval |
| **SageMaker API** | Source of truth for all ML resources |
| **Cost Explorer** | Retrieves real spend data for the current month |
| **Pricing API** | Fetches live instance prices (always current) |
| **S3** | Stores JSON and Markdown reports — versioned, no public access |
| **SNS** | Sends notifications and handles human approval (waitForTaskToken) |
| **EventBridge** | Triggers the workflow every Monday at 8:00 UTC |
| **IAM** | Least-privilege roles — Lambda and Step Functions have separate roles |
| **CloudWatch** | Log groups for both Lambda functions (7-day retention) |

---

## Infrastructure (Terraform)

State is stored remotely in S3 with DynamoDB locking — never committed to git.

```
# Bootstrap (one-time, before terraform init)
aws s3 mb s3://ml-cost-optimizer-tfstate --region eu-west-1
aws s3api put-bucket-versioning \
  --bucket ml-cost-optimizer-tfstate \
  --versioning-configuration Status=Enabled
aws dynamodb create-table \
  --table-name ml-cost-optimizer-tflock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region eu-west-1

# Deploy
cd terraform
terraform init
terraform apply -var="notification_email=your@email.com"
```

---

## CI/CD (GitHub Actions)

Single workflow `ci.yml` — 5 jobs in sequence:

```
lint → test (coverage ≥ 80%) → build zip
                ↓
         security (checkov)
                ↓
         deploy (main only, OIDC auth)
```

- **OIDC authentication** — no AWS keys stored in GitHub secrets
- **Lambda zip** includes all 3 Python files + dependencies installed via pip
- **Checkov** scans Terraform for IaC security issues (soft fail — alerts only)
- **Deploy** only triggers on push to main, never on PRs

---

## Security

- IAM least-privilege — separate roles for Lambda and Step Functions
- OIDC for CI/CD — no long-term AWS credentials in GitHub
- No hardcoded ARNs or account IDs — all Terraform references
- S3 reports: encrypted (SSE-AES256), versioned, public access blocked
- `action.py` executes only after explicit human approval (waitForTaskToken)
- All actions logged via Lambda Powertools (structured JSON)
- pre-commit hooks: ruff (lint) + detect-secrets (secret scanning)

---

## Local Development

```bash
# 1. Set credentials
$env:AWS_ACCESS_KEY_ID="..."
$env:AWS_SECRET_ACCESS_KEY="..."
$env:AWS_DEFAULT_REGION="eu-west-1"

# 2. Install dependencies
pip install -r requirements.txt -r requirements-dev.txt -r lambda/requirements.txt

# 3. Run locally (mock mode — no real AWS calls)
cd lambda
python main.py

# 4. Run tests
pytest tests/ --cov=lambda --cov-fail-under=80 -v
```

---

## Known limitations

### Cost Explorer breakdown
`get_real_costs()` gets the total SageMaker cost but distributes it across resource
types using fixed percentages (25% notebooks, 35% training, etc.). Ideally this
should use real Cost Explorer dimension grouping by usage type for accurate
per-resource costs.

### Carbon footprint in reports
`calculate_carbon_footprint()` collects CO2 estimates per notebook but this data
is not yet included in the S3 reports or SNS notification. A dedicated section
in the Markdown report is planned.
