import json
import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal

def handler(event, context):
    """
    Analyze AWS SageMaker costs and generate optimization recommendations
    """

    print("Starting ML Cost Analysis...")

    # AWS Clients
    ce_client = boto3.client('ce')
    s3_client = boto3.client('s3')

    # Configuration
    bucket_name = os.environ.get('REPORT_BUCKET')
    project_name = os.environ.get('PROJECT_NAME', 'ml-cost-optimizer')

    # Analysis period: last 30 days
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)

    print(f"Analyzing period: {start_date} to {end_date}")

    try:
        # Get SageMaker costs
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': str(start_date),
                'End': str(end_date)
            },
            Granularity='MONTHLY',
            Filter={
                'Dimensions': {
                    'Key': 'SERVICE',
                    'Values': ['Amazon SageMaker']
                }
            },
            Metrics=['UnblendedCost']
        )

        # Calculate total cost
        total_cost = Decimal('0')
        if response.get('ResultsByTime'):
            for result in response['ResultsByTime']:
                cost = result['Total']['UnblendedCost']['Amount']
                total_cost += Decimal(cost)

        total_cost_float = float(total_cost)

        print(f"Total SageMaker cost: ${total_cost_float:.2f}")

        # Generate recommendations
        recommendations = generate_recommendations(total_cost_float)

        # Calculate potential savings
        total_savings = sum(r['monthly_savings'] for r in recommendations)

        # Create report
        report = {
            'metadata': {
                'analysis_date': datetime.now().isoformat(),
                'period_start': str(start_date),
                'period_end': str(end_date),
                'project': project_name
            },
            'costs': {
                'total_monthly_usd': round(total_cost_float, 2),
                'currency': 'USD'
            },
            'optimization': {
                'potential_monthly_savings': round(total_savings, 2),
                'potential_annual_savings': round(total_savings * 12, 2),
                'savings_percentage': round((total_savings / total_cost_float * 100) if total_cost_float > 0 else 0, 1)
            },
            'recommendations': recommendations,
            'summary': {
                'total_recommendations': len(recommendations),
                'high_priority': len([r for r in recommendations if r['priority'] == 'HIGH']),
                'medium_priority': len([r for r in recommendations if r['priority'] == 'MEDIUM']),
                'low_priority': len([r for r in recommendations if r['priority'] == 'LOW'])
            }
        }

        # Save to S3
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        s3_key = f"reports/{timestamp}_cost-analysis.json"

        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=json.dumps(report, indent=2),
            ContentType='application/json'
        )

        print(f"Report saved to s3://{bucket_name}/{s3_key}")

        # Return summary
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Cost analysis completed successfully',
                'total_cost': report['costs']['total_monthly_usd'],
                'potential_savings': report['optimization']['potential_monthly_savings'],
                'savings_percentage': report['optimization']['savings_percentage'],
                'report_location': f's3://{bucket_name}/{s3_key}',
                'recommendations_count': report['summary']['total_recommendations']
            }, indent=2)
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to analyze costs'
            })
        }


def generate_recommendations(total_cost):
    """
    Generate optimization recommendations based on AWS best practices
    """

    recommendations = []

    # Recommendation 1: Notebook Auto-Stop
    if total_cost > 50:
        notebook_savings = total_cost * 0.25
        recommendations.append({
            'id': 'rec-001',
            'priority': 'HIGH',
            'category': 'Compute Optimization',
            'resource_type': 'SageMaker Notebook Instances',
            'issue': 'Notebook instances running 24/7 without auto-stop configuration',
            'recommendation': 'Implement lifecycle configurations to automatically stop notebooks after 1 hour of inactivity',
            'monthly_savings': round(notebook_savings, 2),
            'annual_savings': round(notebook_savings * 12, 2),
            'implementation_effort': 'Low (15-30 minutes)',
            'implementation_steps': [
                'Create a lifecycle configuration with auto-stop script',
                'Attach lifecycle config to existing notebooks',
                'Set idle timeout to 1 hour'
            ],
            'aws_documentation': 'https://docs.aws.amazon.com/sagemaker/latest/dg/notebook-lifecycle-config.html'
        })

    # Recommendation 2: Spot Instances for Training
    if total_cost > 100:
        training_savings = total_cost * 0.35
        recommendations.append({
            'id': 'rec-002',
            'priority': 'HIGH',
            'category': 'Cost Optimization',
            'resource_type': 'SageMaker Training Jobs',
            'issue': 'Training jobs running on expensive On-Demand instances',
            'recommendation': 'Switch to Managed Spot Training for up to 70% cost reduction',
            'monthly_savings': round(training_savings, 2),
            'annual_savings': round(training_savings * 12, 2),
            'implementation_effort': 'Medium (1-2 hours)',
            'implementation_steps': [
                'Enable Managed Spot Training in SageMaker training job configuration',
                'Set max wait time and max runtime appropriately',
                'Implement checkpointing for long-running jobs'
            ],
            'aws_documentation': 'https://docs.aws.amazon.com/sagemaker/latest/dg/model-managed-spot-training.html'
        })

    # Recommendation 3: Endpoint Auto-Scaling
    if total_cost > 200:
        endpoint_savings = total_cost * 0.20
        recommendations.append({
            'id': 'rec-003',
            'priority': 'MEDIUM',
            'category': 'Scaling Optimization',
            'resource_type': 'SageMaker Inference Endpoints',
            'issue': 'Always-on endpoints with variable traffic patterns',
            'recommendation': 'Configure auto-scaling based on invocations per instance and implement scheduled scaling',
            'monthly_savings': round(endpoint_savings, 2),
            'annual_savings': round(endpoint_savings * 12, 2),
            'implementation_effort': 'Medium (2-3 hours)',
            'implementation_steps': [
                'Define scaling policy based on InvocationsPerInstance metric',
                'Set min/max instance counts appropriately',
                'Configure scheduled scaling for predictable low-traffic periods',
                'Consider serverless inference for sporadic workloads'
            ],
            'aws_documentation': 'https://docs.aws.amazon.com/sagemaker/latest/dg/endpoint-auto-scaling.html'
        })

    # Recommendation 4: S3 Lifecycle Policies
    storage_savings = total_cost * 0.05
    recommendations.append({
        'id': 'rec-004',
        'priority': 'LOW',
        'category': 'Storage Optimization',
        'resource_type': 'S3 (Training Data & Model Artifacts)',
        'issue': 'All training data and model artifacts stored in S3 Standard storage class',
        'recommendation': 'Implement S3 lifecycle policies to transition old data to cheaper storage classes',
        'monthly_savings': round(storage_savings, 2),
        'annual_savings': round(storage_savings * 12, 2),
        'implementation_effort': 'Low (30 minutes)',
        'implementation_steps': [
            'Identify S3 buckets used by SageMaker',
            'Create lifecycle policy: Standard -> Intelligent-Tiering after 30 days',
            'Move artifacts older than 90 days to Glacier',
            'Delete old experiment artifacts after 1 year (if not needed)'
        ],
        'aws_documentation': 'https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html'
    })

    # Recommendation 5: Reserved Capacity (if high costs)
    if total_cost > 500:
        reserved_savings = total_cost * 0.30
        recommendations.append({
            'id': 'rec-005',
            'priority': 'MEDIUM',
            'category': 'Commitment Discount',
            'resource_type': 'SageMaker Compute',
            'issue': 'High baseline compute usage without commitment discounts',
            'recommendation': 'Purchase SageMaker Savings Plans for predictable workloads (up to 64% savings)',
            'monthly_savings': round(reserved_savings, 2),
            'annual_savings': round(reserved_savings * 12, 2),
            'implementation_effort': 'Low (1 hour analysis + purchase)',
            'implementation_steps': [
                'Analyze usage patterns over past 30-60 days',
                'Identify baseline consistent compute usage',
                'Purchase 1-year or 3-year SageMaker Savings Plan',
                'Monitor coverage and utilization monthly'
            ],
            'aws_documentation': 'https://docs.aws.amazon.com/savingsplans/latest/userguide/what-is-savings-plans.html'
        })

    return recommendations
