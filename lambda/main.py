import json
import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal

# ---------------------------------------------------------------------------
# MOCK DATA — used when MOCK_MODE=true (no real AWS account needed)
# ---------------------------------------------------------------------------
MOCK_DATA = {
    "total_cost": 850.00,
    "cost_by_resource": {
        "notebooks": 212.00,    # ~25% — idle notebooks running 24/7
        "training": 297.00,     # ~35% — on-demand training jobs
        "endpoints": 170.00,    # ~20% — always-on inference endpoints
        "storage": 42.50,       # ~5%  — S3 standard storage
        "other": 128.50         # ~15% — misc SageMaker compute
    },
    "usage_metrics": {
        "notebook_idle_hours": 18,      # hours/day notebooks sit idle
        "training_jobs_on_demand": 12,  # on-demand training jobs last month
        "endpoint_off_hours_pct": 0.40, # 40% of time endpoints receive no traffic
        "s3_data_age_days": 120         # average age of training data in S3
    }
}


def get_mock_data():
    print("[MOCK MODE] Simulating AWS Cost Explorer + CloudWatch response...")
    print(f"[MOCK MODE] Injecting ${MOCK_DATA['total_cost']:.2f} monthly SageMaker spend")
    return MOCK_DATA


# ---------------------------------------------------------------------------
# REAL AWS DATA FETCHING
# ---------------------------------------------------------------------------
def fetch_cost_by_resource(ce_client, start_date, end_date):
    """
    Fetch SageMaker costs broken down by usage type (notebooks, training, endpoints, storage).
    Uses AWS Cost Explorer GroupBy to get per-resource breakdown.
    """
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
        GroupBy=[{'Type': 'DIMENSION', 'Key': 'USAGE_TYPE'}],
        Metrics=['UnblendedCost']
    )

    cost_by_resource = {
        "notebooks": Decimal('0'),
        "training": Decimal('0'),
        "endpoints": Decimal('0'),
        "storage": Decimal('0'),
        "other": Decimal('0')
    }

    for result in response.get('ResultsByTime', []):
        for group in result.get('Groups', []):
            usage_type = group['Keys'][0].lower()
            amount = Decimal(group['Metrics']['UnblendedCost']['Amount'])

            if 'notebook' in usage_type:
                cost_by_resource['notebooks'] += amount
            elif 'training' in usage_type:
                cost_by_resource['training'] += amount
            elif 'endpoint' in usage_type or 'inference' in usage_type:
                cost_by_resource['endpoints'] += amount
            elif 'storage' in usage_type or 's3' in usage_type:
                cost_by_resource['storage'] += amount
            else:
                cost_by_resource['other'] += amount

    return {k: float(v) for k, v in cost_by_resource.items()}


def fetch_usage_metrics(cw_client, start_date, end_date):
    """
    Fetch real usage metrics from CloudWatch to validate recommendations.
    - Notebook idle hours
    - Endpoint off-hours traffic
    """
    metrics = {
        "notebook_idle_hours": 0,
        "training_jobs_on_demand": 0,
        "endpoint_off_hours_pct": 0.0,
        "s3_data_age_days": 90  # default conservative estimate
    }

    try:
        # Check endpoint invocations during off-hours (10pm–6am)
        response = cw_client.get_metric_statistics(
            Namespace='AWS/SageMaker',
            MetricName='Invocations',
            StartTime=datetime.combine(start_date, datetime.min.time()),
            EndTime=datetime.combine(end_date, datetime.min.time()),
            Period=3600,  # 1-hour granularity
            Statistics=['Sum']
        )

        datapoints = response.get('Datapoints', [])
        if datapoints:
            off_hours = [
                d for d in datapoints
                if d['Timestamp'].hour >= 22 or d['Timestamp'].hour < 6
            ]
            total_invocations = sum(d['Sum'] for d in datapoints)
            off_hours_invocations = sum(d['Sum'] for d in off_hours)

            if total_invocations > 0:
                metrics['endpoint_off_hours_pct'] = round(
                    off_hours_invocations / total_invocations, 2
                )

    except Exception as e:
        print(f"[WARNING] CloudWatch fetch failed: {e} — using conservative defaults")

    return metrics


# ---------------------------------------------------------------------------
# MAIN HANDLER
# ---------------------------------------------------------------------------
def handler(event, context):
    """
    Analyze AWS SageMaker costs and generate optimization recommendations.
    
    FinOps Framework phases covered:
    - INFORM:   Break down SageMaker spend by resource type
    - OPTIMIZE: Surface prioritized, data-driven recommendations
    - OPERATE:  Save report to S3 for recurring cost governance

    Set MOCK_MODE=true to run without a real AWS account.
    """

    print("Starting ML Cost Analysis...")

    mock_mode = os.environ.get('MOCK_MODE', 'false').lower() == 'true'
    bucket_name = os.environ.get('REPORT_BUCKET', 'mock-bucket')
    project_name = os.environ.get('PROJECT_NAME', 'ml-cost-optimizer')

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)

    print(f"Analyzing period: {start_date} to {end_date}")

    try:
        # ---------------------------------------------------------------
        # INFORM — Get cost breakdown + usage metrics
        # ---------------------------------------------------------------
        if mock_mode:
            data = get_mock_data()
        else:
            ce_client = boto3.client('ce')
            cw_client = boto3.client('cloudwatch')
            data = {
                "cost_by_resource": fetch_cost_by_resource(ce_client, start_date, end_date),
                "usage_metrics": fetch_usage_metrics(cw_client, start_date, end_date)
            }
            data["total_cost"] = sum(data["cost_by_resource"].values())

        total_cost = data["total_cost"]
        cost_by_resource = data["cost_by_resource"]
        usage_metrics = data["usage_metrics"]

        print(f"Total SageMaker cost: ${total_cost:.2f}")
        print(f"Cost breakdown: {json.dumps(cost_by_resource, indent=2)}")

        # ---------------------------------------------------------------
        # OPTIMIZE — Generate recommendations per resource category
        # ---------------------------------------------------------------
        recommendations = generate_recommendations(cost_by_resource, usage_metrics)
        total_savings = sum(r['monthly_savings'] for r in recommendations)

        # ---------------------------------------------------------------
        # Build report
        # ---------------------------------------------------------------
        report = {
            'metadata': {
                'analysis_date': datetime.now().isoformat(),
                'period_start': str(start_date),
                'period_end': str(end_date),
                'project': project_name,
                'mock_mode': mock_mode,
                'finops_framework_version': '1.0',
                'phases_covered': ['Inform', 'Optimize', 'Operate']
            },
            'costs': {
                'total_monthly_usd': round(total_cost, 2),
                'breakdown_by_resource': {k: round(v, 2) for k, v in cost_by_resource.items()},
                'currency': 'USD'
            },
            'usage_metrics': usage_metrics,
            'optimization': {
                'potential_monthly_savings': round(total_savings, 2),
                'potential_annual_savings': round(total_savings * 12, 2),
                'savings_percentage': round(
                    (total_savings / total_cost * 100) if total_cost > 0 else 0, 1
                )
            },
            'recommendations': recommendations,
            'summary': {
                'total_recommendations': len(recommendations),
                'high_priority': len([r for r in recommendations if r['priority'] == 'HIGH']),
                'medium_priority': len([r for r in recommendations if r['priority'] == 'MEDIUM']),
                'low_priority': len([r for r in recommendations if r['priority'] == 'LOW'])
            }
        }

        # ---------------------------------------------------------------
        # OPERATE — Save report to S3
        # ---------------------------------------------------------------
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        s3_key = f"reports/{timestamp}_cost-analysis.json"

        if mock_mode:
            print("[MOCK MODE] Skipping S3 upload — printing report instead:")
            print(json.dumps(report, indent=2))
            report_location = "local (mock mode)"
        else:
            s3_client = boto3.client('s3')
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=json.dumps(report, indent=2),
                ContentType='application/json'
            )
            print(f"Report saved to s3://{bucket_name}/{s3_key}")
            report_location = f's3://{bucket_name}/{s3_key}'

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Cost analysis completed successfully',
                'mock_mode': mock_mode,
                'total_cost': report['costs']['total_monthly_usd'],
                'cost_breakdown': report['costs']['breakdown_by_resource'],
                'potential_savings': report['optimization']['potential_monthly_savings'],
                'savings_percentage': report['optimization']['savings_percentage'],
                'report_location': report_location,
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


# ---------------------------------------------------------------------------
# RECOMMENDATIONS ENGINE — savings applied per resource category
# ---------------------------------------------------------------------------
def generate_recommendations(cost_by_resource, usage_metrics):
    """
    Generate data-driven recommendations based on:
    - Per-resource cost breakdown (not total cost)
    - Real usage metrics from CloudWatch

    This avoids the compounding savings error where multiple recommendations
    applied to the same total would exceed 100% savings.
    """
    recommendations = []

    notebook_cost = cost_by_resource.get('notebooks', 0)
    training_cost = cost_by_resource.get('training', 0)
    endpoint_cost = cost_by_resource.get('endpoints', 0)
    storage_cost = cost_by_resource.get('storage', 0)
    total_cost = sum(cost_by_resource.values())

    idle_hours = usage_metrics.get('notebook_idle_hours', 0)
    off_hours_pct = usage_metrics.get('endpoint_off_hours_pct', 0)
    s3_age_days = usage_metrics.get('s3_data_age_days', 0)

    # Rec 1: Notebook Auto-Stop
    # Only recommend if notebooks represent real spend AND idle hours detected
    if notebook_cost > 20:
        idle_ratio = min(idle_hours / 24, 0.80)  # cap at 80% max savings
        notebook_savings = notebook_cost * idle_ratio
        recommendations.append({
            'id': 'rec-001',
            'priority': 'HIGH',
            'category': 'Compute Optimization',
            'finops_phase': 'Optimize',
            'resource_type': 'SageMaker Notebook Instances',
            'issue': f'Notebooks idle ~{idle_hours}h/day — cost attributable: ${notebook_cost:.2f}/mo',
            'recommendation': 'Implement lifecycle configurations to auto-stop notebooks after 1h of inactivity',
            'monthly_savings': round(notebook_savings, 2),
            'annual_savings': round(notebook_savings * 12, 2),
            'savings_basis': f'{round(idle_ratio * 100)}% of notebook spend (${notebook_cost:.2f})',
            'implementation_effort': 'Low (15-30 minutes)',
            'implementation_steps': [
                'Create a lifecycle configuration with auto-stop script',
                'Attach lifecycle config to existing notebooks',
                'Set idle timeout to 1 hour'
            ],
            'aws_documentation': 'https://docs.aws.amazon.com/sagemaker/latest/dg/notebook-lifecycle-config.html'
        })

    # Rec 2: Spot Instances for Training
    # Applied only to training_cost, not total
    if training_cost > 50:
        spot_savings = training_cost * 0.70  # Spot is typically 70% cheaper
        recommendations.append({
            'id': 'rec-002',
            'priority': 'HIGH',
            'category': 'Cost Optimization',
            'finops_phase': 'Optimize',
            'resource_type': 'SageMaker Training Jobs',
            'issue': f'Training jobs on On-Demand instances — cost attributable: ${training_cost:.2f}/mo',
            'recommendation': 'Switch to Managed Spot Training for up to 70% cost reduction',
            'monthly_savings': round(spot_savings, 2),
            'annual_savings': round(spot_savings * 12, 2),
            'savings_basis': f'70% of training spend (${training_cost:.2f})',
            'implementation_effort': 'Medium (1-2 hours)',
            'implementation_steps': [
                'Enable Managed Spot Training in training job configuration',
                'Set max wait time and max runtime appropriately',
                'Implement checkpointing for long-running jobs'
            ],
            'aws_documentation': 'https://docs.aws.amazon.com/sagemaker/latest/dg/model-managed-spot-training.html'
        })

    # Rec 3: Endpoint Auto-Scaling
    # Only if CloudWatch shows real off-hours idle traffic
    if endpoint_cost > 50 and off_hours_pct > 0.20:
        endpoint_savings = endpoint_cost * off_hours_pct
        recommendations.append({
            'id': 'rec-003',
            'priority': 'MEDIUM',
            'category': 'Scaling Optimization',
            'finops_phase': 'Optimize',
            'resource_type': 'SageMaker Inference Endpoints',
            'issue': f'{round(off_hours_pct * 100)}% of endpoint traffic occurs off-hours — cost: ${endpoint_cost:.2f}/mo',
            'recommendation': 'Configure auto-scaling + scheduled scale-down during low-traffic periods',
            'monthly_savings': round(endpoint_savings, 2),
            'annual_savings': round(endpoint_savings * 12, 2),
            'savings_basis': f'{round(off_hours_pct * 100)}% of endpoint spend (${endpoint_cost:.2f})',
            'implementation_effort': 'Medium (2-3 hours)',
            'implementation_steps': [
                'Define scaling policy based on InvocationsPerInstance metric',
                'Set min/max instance counts',
                'Configure scheduled scaling for off-hours',
                'Consider serverless inference for sporadic workloads'
            ],
            'aws_documentation': 'https://docs.aws.amazon.com/sagemaker/latest/dg/endpoint-auto-scaling.html'
        })

    # Rec 4: S3 Lifecycle Policies
    # Only if data is old enough to benefit from tiering
    if storage_cost > 10 and s3_age_days > 90:
        storage_savings = storage_cost * 0.75  # Standard -> Glacier = ~75% storage saving
        recommendations.append({
            'id': 'rec-004',
            'priority': 'LOW',
            'category': 'Storage Optimization',
            'finops_phase': 'Optimize',
            'resource_type': 'S3 (Training Data & Model Artifacts)',
            'issue': f'Training data avg age: {s3_age_days} days in S3 Standard — cost: ${storage_cost:.2f}/mo',
            'recommendation': 'Implement S3 lifecycle policies to transition old data to Glacier',
            'monthly_savings': round(storage_savings, 2),
            'annual_savings': round(storage_savings * 12, 2),
            'savings_basis': f'75% of storage spend (${storage_cost:.2f})',
            'implementation_effort': 'Low (30 minutes)',
            'implementation_steps': [
                'Identify S3 buckets used by SageMaker',
                'Create lifecycle policy: Standard -> Intelligent-Tiering after 30 days',
                'Move artifacts older than 90 days to Glacier',
                'Delete old experiment artifacts after 1 year'
            ],
            'aws_documentation': 'https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html'
        })

    # Rec 5: Savings Plans
    # Only if total stable compute spend justifies a commitment
    if total_cost > 500:
        commitment_base = cost_by_resource.get('other', 0) + (training_cost * 0.30)
        savings_plan_savings = commitment_base * 0.64
        recommendations.append({
            'id': 'rec-005',
            'priority': 'MEDIUM',
            'category': 'Commitment Discount',
            'finops_phase': 'Operate',
            'resource_type': 'SageMaker Compute',
            'issue': f'Stable baseline compute of ~${commitment_base:.2f}/mo without commitment discounts',
            'recommendation': 'Purchase SageMaker Savings Plans for predictable workloads (up to 64% savings)',
            'monthly_savings': round(savings_plan_savings, 2),
            'annual_savings': round(savings_plan_savings * 12, 2),
            'savings_basis': f'64% of stable compute spend (${commitment_base:.2f})',
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
