# 💰 AWS Machine Learning Cost Optimizer

## 🎯 Elevating Business Value through Cloud Efficiency

In the world of Cloud Computing, **unoptimized ML infrastructure is a hidden leak in a company's budget**. As a Technical Customer Success Manager, I built this tool to bridge the gap between high-performance Machine Learning and financial sustainability.

This Python-based tool analyzes AWS SageMaker workloads to provide **actionable cost-optimization recommendations**, helping organizations achieve more with less.

---

## 🚀 Business Impact (Estimations)

This tool isn't just about code; it's about **ROI**. Based on typical AWS Well-Architected reviews, here is the estimated impact of implementing the recommendations:

| Optimization Lever | Estimated Savings | Business Logic |
| :--- | :--- | :--- |
| **Managed Spot Training** | 60% - 90% | Leverages spare AWS capacity for non-urgent training jobs. |
| **Instance Right-sizing** | 20% - 45% | Identifies over-provisioned notebooks and endpoints. |
| **Lifecycle Configurations** | 10% - 15% | Automatically shuts down idle resources after hours. |
| **S3 Lifecycle Policies** | 5% - 10% | Moves old model artifacts to colder storage tiers. |

> **Note:** These results are estimations based on AWS pricing models and simulated usage patterns.

---

## 🛠️ Technical Implementation

### How it works (The Compass)
The script interacts with AWS APIs to audit your environment and compare current usage against cost-optimized alternatives.

* **Core Engine:** Python 3.x
* **AWS SDK:** Boto3 (Cost Explorer & SageMaker APIs)
* **Strategy:** Well-Architected Framework - Cost Optimization Pillar

### Quick Start (Manual)
1. **Clone the ship:**
   ```bash
   git clone [https://github.com/mboumhawahaga-ship-it/aws-machine-learning-cost-optimizer.git](https://github.com/mboumhawahaga-ship-it/aws-machine-learning-cost-optimizer.git)
   cd aws-machine-learning-cost-optimizer
