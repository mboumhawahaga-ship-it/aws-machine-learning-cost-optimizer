[![Quality Check](https://github.com/mboumhawahaga-ship-it/aws-machine-learning-cost-optimizer/actions/workflows/ci-quality.yml/badge.svg)](https://github.com/mboumhawahaga-ship-it/aws-machine-learning-cost-optimizer/actions/workflows/ci-quality.yml)
[![CI/CD Tests](https://github.com/mboumhawahaga-ship-it/aws-machine-learning-cost-optimizer/actions/workflows/ci.yml/badge.svg)](https://github.com/mboumhawahaga-ship-it/aws-machine-learning-cost-optimizer/actions/workflows/ci.yml)
![License](https://img.shields.io/badge/license-MIT-blue)

# Cut your SageMaker bill by 40–60% automatically

---

## The Problem

- SageMaker notebooks run 24/7 even when no one is using them — you pay for idle machines
- Training jobs run at full price when Spot instances cost 70% less for the same work
- Nobody gets an alert until the monthly AWS invoice arrives

---

## The Solution

This tool scans your AWS environment every week, identifies what is being wasted, and sends you a plain-English report with the exact savings available — broken down by resource, sorted by impact.

No dashboards to configure. No agents to manage. One email every Monday morning.

```
Every Monday 8:00 AM
       ↓
Scan all SageMaker resources
       ↓
Calculate real savings (live AWS prices)
       ↓
Email report to your team
```

---

## Real Numbers

Prices pulled live from the AWS Pricing API — always current.

| What's being wasted | Typical monthly cost | Savings available | Effort |
|---|---|---|---|
| Notebooks left running | $70–$212 / notebook | **75%** with auto-stop | Low |
| Training on On-Demand | $100–$500 / job | **70%** with Spot instances | Medium |
| Idle inference endpoints | $50–$170 / endpoint | **30%** with auto-scaling | Medium |
| Old data in S3 Standard | $23 / TB | **83%** moved to Glacier | Low |

**Example — team spending $850/month:**

| Month | Spend | Change |
|---|---|---|
| Before | $850 | baseline |
| Month 1 (quick wins) | $620 | −27% |
| Month 2 (full optimization) | $480 | −44% |
| **Annual savings** | **$4,440** | |

---

## How It Works

**1. Scan** — Every Monday, the tool connects to your AWS account and lists every SageMaker resource running (notebooks, training jobs, endpoints, storage).

**2. Report** — It calculates the real cost of each resource using live AWS prices, identifies what can be reduced, and generates a prioritized report with exact dollar amounts.

**3. Approve or ignore** — You receive an email with the recommendations. Nothing is changed automatically. Your team decides what to act on.

---

## Setup in 2 Minutes

You need an AWS account and Terraform installed. That's it.

```bash
cd terraform
terraform init
terraform apply -var="notification_email=your@email.com"
```

Confirm the subscription email from AWS, and your first report arrives next Monday.

**What gets deployed:** one serverless function, one S3 bucket for report storage, one email notification. Infrastructure cost: under $1/month.

---

## Sample Report

See a full example: [docs/samples/report-example.md](docs/samples/report-example.md)

---

---

## For Recruiters / Technical Details

**Stack:** Python 3.12 · AWS Lambda · Step Functions · Terraform · GitHub Actions

**AWS services:** Lambda · SageMaker API · Cost Explorer · Pricing API · S3 · SNS · EventBridge · IAM · CloudWatch

**What this demonstrates:**
- Serverless architecture with least-privilege IAM (separate policy per action)
- Real-time pricing via AWS Pricing API with graceful fallback
- GDPR compliance checks on SageMaker resources (owner, data-classification, expiration-date tags)
- Carbon footprint estimation per instance type
- Structured logging with AWS Lambda Powertools
- Step Functions workflow with JSONata, retry + exponential backoff
- pytest test suite with moto (AWS mocking), ruff linting, pre-commit hooks
- CI/CD via GitHub Actions on every push to main

**Project structure:**
```
lambda/       ← 3 Python files: discovery, analysis, action
terraform/    ← full IaC: Lambda, Step Functions, IAM, EventBridge, S3, SNS
tests/        ← pytest suite with mocked AWS APIs
docs/         ← architecture documentation and sample reports
scripts/      ← setup utilities
```

Full architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
