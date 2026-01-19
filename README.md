# AWS ML Cost Optimizer

> Automated cost analysis and optimization recommendations for AWS SageMaker workloads

[![Terraform](https://img.shields.io/badge/Terraform-1.0+-623CE4?logo=terraform)](https://www.terraform.io/)
[![AWS](https://img.shields.io/badge/AWS-Lambda-FF9900?logo=amazon-aws)](https://aws.amazon.com/lambda/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)](https://www.python.org/)

## The Problem

Machine Learning infrastructure costs on AWS can spiral out of control:

- **Notebook instances** running 24/7 while developers are offline
- **Training jobs** using expensive On-Demand instead of Spot (70% cheaper)
- **Inference endpoints** always-on during low-traffic periods
- **No visibility** into optimization opportunities

**Result:** Companies waste **40-70% of their ML budget**

## The Solution

Automated serverless solution that:

- Analyzes AWS SageMaker costs via Cost Explorer API
- Identifies specific optimization opportunities
- Calculates exact savings potential
- Generates actionable JSON reports with implementation steps
- Fully automated with Infrastructure-as-Code (Terraform)

## Real Impact

**Example Analysis Results:**

On a sample account spending **$850/month** on SageMaker:

| Optimization | Monthly Savings | Annual Savings | Effort |
|-------------|----------------|----------------|--------|
| Notebook auto-stop | $212 | $2,544 | Low (15min) |
| Spot training | $297 | $3,564 | Medium (1h) |
| Endpoint auto-scaling | $170 | $2,040 | Medium (2h) |
| S3 lifecycle policies | $42 | $504 | Low (30min) |
| **TOTAL** | **$721 (85%)** | **$8,652** | **~1 week** |

**ROI:** Immediate cost reduction with minimal implementation effort

## 💰 Simulation d'Impact Financier (Exemple)

Voici une estimation des économies réalisables pour un client type utilisant des charges de travail ML intensives :

| Levier d'Optimisation | Gain Estimé | Impact sur la Facture |
| :--- | :--- | :--- |
| **Instances Spot** | 60% à 90% | Réduction massive sur le Training |
| **Right-sizing** | 20% à 40% | Ajustement des instances sous-utilisées |
| **Nettoyage EBS** | 5% à 10% | Suppression des volumes isolés |

> **Note :** Ces chiffres sont des estimations basées sur les meilleures pratiques AWS et les simulations effectuées par l'outil

## Architecture

```
┌───────────────────────────────────────────────────────┐
│                    AWS Account                        │
│                                                       │
│  ┌─────────────────┐      ┌──────────────────┐      │
│  │  Lambda         │─────>│  Cost Explorer   │      │
│  │  Function       │      │  API             │      │
│  │  (Python 3.11)  │      └──────────────────┘      │
│  └────────┬────────┘                                 │
│           │                                           │
│           │ Saves report                             │
│           ▼                                           │
│  ┌─────────────────┐                                 │
│  │  S3 Bucket      │                                 │
│  │  (JSON Reports) │                                 │
│  └─────────────────┘                                 │
│                                                       │
│  Deployed via Terraform (IaC)                        │
└───────────────────────────────────────────────────────┘
```

**Technology Stack:**
- **IaC:** Terraform (reproducible, version-controlled)
- **Compute:** AWS Lambda (serverless, pay-per-execution)
- **Data:** AWS Cost Explorer API
- **Storage:** Amazon S3
- **Language:** Python 3.11

## Project Structure

```
ml-cost-optimizer/
├── terraform/              # Infrastructure as Code
│   ├── main.tf            # Main Terraform configuration
│   ├── variables.tf       # Input variables
│   └── outputs.tf         # Output values
├── lambda/                # Lambda function code
│   ├── main.py           # Python handler and logic
│   └── requirements.txt  # Python dependencies
└── README.md            # This file
```

## Quick Start

### Prerequisites

- AWS Account with appropriate permissions
- [Terraform](https://www.terraform.io/downloads) >= 1.0
- [AWS CLI](https://aws.amazon.com/cli/) configured with credentials
- PowerShell (Windows) or zip utility (Linux/Mac)

### Installation

**Step 1: Clone the repository**
```bash
git clone https://github.com/mboumhawahaga-ship-it/terraform-aws-learning.git
cd terraform-aws-learning/ml-cost-optimizer
```

**Step 2: Create Lambda deployment package**

On Windows (PowerShell):
```powershell
cd lambda
Compress-Archive -Path main.py -DestinationPath function.zip
cd ..
```

On Linux/Mac:
```bash
cd lambda
zip function.zip main.py
cd ..
```

**Step 3: Deploy infrastructure with Terraform**
```bash
cd terraform

# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Deploy infrastructure
terraform apply
```

Type `yes` when prompted. Deployment takes approximately 2 minutes.

**Step 4: Note the outputs**

After deployment, Terraform will display:
```
Outputs:

lambda_function_arn = "arn:aws:lambda:eu-west-1:ACCOUNT_ID:function:ml-cost-optimizer-analyzer"
lambda_function_name = "ml-cost-optimizer-analyzer"
s3_bucket_arn = "arn:aws:s3:::ml-cost-optimizer-reports-XXXXX"
s3_bucket_name = "ml-cost-optimizer-reports-XXXXX"
```

## Usage

### Manual Execution

Test the Lambda function manually:

```bash
aws lambda invoke \
  --function-name ml-cost-optimizer-analyzer \
  --region eu-west-1 \
  output.json

cat output.json
```

### View Generated Reports

```bash
# Get bucket name from Terraform output
BUCKET=$(cd terraform && terraform output -raw s3_bucket_name)

# List reports
aws s3 ls s3://$BUCKET/reports/

# Download latest report
aws s3 cp s3://$BUCKET/reports/LATEST_REPORT.json report.json

# View with formatting (requires jq)
cat report.json | jq
```

## Configuration

### Customize AWS Region

Edit `terraform/variables.tf`:
```hcl
variable "aws_region" {
  default = "us-east-1"  # Change to your preferred region
}
```

### Customize Project Name

Edit `terraform/variables.tf`:
```hcl
variable "project_name" {
  default = "my-ml-optimizer"  # Customize resource names
}
```

## Cleanup

To destroy all created resources:

```bash
cd terraform
terraform destroy
```

Type `yes` when prompted.

## Author

**mboumhawahaga-ship-it**

- GitHub: [@mboumhawahaga-ship-it](https://github.com/mboumhawahaga-ship-it)
- Email: mboumhawahaga@gmail.com

---

**Interested in reducing your ML costs by 40-70%?**
This solution provides immediate, actionable insights with minimal implementation effort.
