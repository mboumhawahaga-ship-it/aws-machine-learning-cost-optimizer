# AWS Machine Learning Cost Optimizer

![Quality & Security Check](https://github.com/mboumhawahaga-ship-it/Aws-tagging-gouvernance/actions/workflows/ci-quality.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue)

## Features
| Feature                      | Description                                       |
|------------------------------|---------------------------------------------------|
| Cost Analysis                | Analyzes costs efficiently                        |
| Visualizations               | Provides graphical representations of costs       |
| Optimization Recommendations   | Offers suggestions for cost savings                |

## Prerequisites
- AWS Account
- Necessary IAM permissions

## Installation
### Local Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/mboumhawahaga-ship-it/aws-machine-learning-cost-optimizer
   cd aws-machine-learning-cost-optimizer
   ```
2. Install the requirements:
   ```bash
   pip install -r requirements.txt
   ```

### AWS Lambda Installation
1. Zip your project folder:
   ```bash
   zip -r lambda_function.zip .
   ```
2. Upload `lambda_function.zip` to your AWS Lambda console.

## Quick Start Guide
1. Set up your AWS credentials.
2. Run the optimizer:
   ```bash
   python optimize_costs.py
   ```

## Architecture
![Architecture Diagram](link_to_architecture_diagram.png)

## Example Outputs
- Cost Analysis: ```{ "service": "Amazon S3", "cost": "$100" }``` 
- Optimization Suggestions: ```{ "service": "EC2", "suggested_cost": "$70" }``` 

## Customization Guide
Modify parameters in `config.yaml` to tailor behavior to your needs.

## Troubleshooting FAQ
- **Q: What if I encounter permission issues?**  
  A: Ensure your IAM role has the necessary permissions.
- **Q: The optimizer fails to run. Why?**  
  A: Check if the AWS credentials are correctly configured.

## Expected Outcomes
- Enhanced visibility over costs
- Actionable insights for optimization

## Resources
- [AWS Documentation](https://docs.aws.amazon.com/)
- [ML Cost Optimization Guide](https://aws.amazon.com/machine-learning/)

## Contributing Guidelines
1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/fooBar`).
3. Commit your changes (`git commit -am 'Add some fooBar'`).
4. Push to the branch (`git push origin feature/fooBar`).
5. Open a Pull Request.

## Roadmap
- Expand features to include more services.
- Implement further optimizations based on user feedback.

--- 
*Documentation last updated on 2026-01-29*
