# Architecture — AWS ML Cost Optimizer

This project automatically scans SageMaker resources, analyzes costs, and takes
optimization actions (with human approval). Everything runs serverless on AWS.

---

## How it works — big picture

```
EventBridge (weekly cron)
        |
        v
 Step Functions Workflow
        |
        |---> [1] Scan-SageMaker     (Lambda: ml-cost-optimizer-analyzer)
        |           Scans all SageMaker resources + fetches real costs
        |
        |---> [2] Analyse-Rapport    (Lambda: ml-cost-optimizer-analyzer)
        |           Generates recommendations sorted by ROI
        |           Saves JSON + Markdown reports to S3
        |
        |---> [3] Action             (Lambda: ml-cost-optimizer-action)
        |           Executes approved actions (stop notebook / delete endpoint)
        |
        |---> [4] Notification       (SNS)
                    Sends email/SMS summary to subscribers
```

---

## Lambda files

### `lambda/discovery.py`
Scans all live SageMaker resources via boto3:
- **`scan_notebooks()`** — lists notebook instances with status, instance type, and carbon footprint estimate
- **`scan_endpoints()`** — lists endpoints with status
- **`scan_training_jobs()`** — lists last 50 completed training jobs
- **`check_rgpd_compliance()`** — checks GDPR tags (`owner`, `data-classification`, `expiration-date`) on each resource
- **`calculate_carbon_footprint()`** — estimates CO2 in kg/month based on instance type
- **`run_discovery()`** — calls all of the above and returns a single report dict including GDPR compliance summary

### `lambda/main.py`
The main analysis Lambda. Entry point for steps 1 and 2 in the workflow:
- **`get_real_costs()`** — queries AWS Cost Explorer for real SageMaker spend this month, falls back to mock data on error
- **`generate_recommendations()`** — produces a prioritized list of savings opportunities (notebooks, training, endpoints, storage)
- **`generate_markdown_report()`** / **`save_markdown_report()`** — builds and uploads a Markdown report to S3
- **`save_json_report()`** — uploads a structured JSON report to S3
- **`send_sns_notification()`** — sends a savings summary via SNS (non-blocking)
- **`handler()`** — Lambda entry point: orchestrates the full analysis flow

### `lambda/action.py`
Executes a single action on a SageMaker resource. **Only runs after human approval.**
- **`stop_notebook(name)`** — stops a notebook instance (no deletion)
- **`delete_endpoint(name)`** — deletes an inactive endpoint
- **`handler(event)`** — reads `action_type` and `resource_name` from the event, routes to the right function, returns 200 or 500

---

## Step Functions workflow — step by step

| Step | State | Lambda | What happens |
|------|-------|--------|--------------|
| 1 | Scan-SageMaker | `ml-cost-optimizer-analyzer` | Scans resources, fetches real costs from Cost Explorer |
| 2 | Analyse-Rapport | `ml-cost-optimizer-analyzer` | Generates recommendations, saves reports to S3 |
| 3 | Action | `ml-cost-optimizer-action` | Executes an approved action (stop/delete) |
| 4 | Notification | SNS (direct integration) | Publishes summary to the SNS topic |

Each Lambda step retries up to 3 times with exponential backoff on AWS transient errors.
The workflow uses the **JSONata** query language for state I/O transformations.

---

## AWS services used

| Service | Why |
|---------|-----|
| **Lambda** | Serverless compute — no infrastructure to manage |
| **Step Functions** | Orchestrates the multi-step workflow with built-in retries and state |
| **SageMaker API** | Source of truth for all ML resources (notebooks, endpoints, training jobs) |
| **Cost Explorer** | Retrieves real spend data for the current month |
| **S3** | Stores JSON and Markdown reports for audit and history |
| **SNS** | Sends notifications (email/SMS) when analysis completes |
| **EventBridge** | Triggers the workflow on a weekly schedule |
| **IAM** | Least-privilege roles — each Lambda only has the permissions it needs |

---

## What's still to do

### Human approval before actions
Right now, step 3 (Action) runs automatically in the workflow. The intent is that
a human reviews the recommendations first and manually approves which action to
take. A **Step Functions Wait for Callback** pattern with a task token needs to be
wired in before the Action state.

### MCP integration
The plan is to expose this optimizer as an **MCP (Model Context Protocol) server**
so an AI assistant can query costs, read recommendations, and trigger approved
actions through natural language.

### Carbon footprint reporting
`calculate_carbon_footprint()` in `discovery.py` currently estimates CO2 per
notebook based on instance type. This data is collected but not yet included in
the S3 reports or the SNS notification. A dedicated CO2 section in the Markdown
report is planned.

### Real GroupBy in Cost Explorer
`get_real_costs()` in `main.py` gets the total SageMaker cost but distributes it
across resource types using fixed percentages (25% notebooks, 35% training, etc.).
Ideally, this should use real Cost Explorer dimension grouping by usage type to get
accurate per-resource costs.
