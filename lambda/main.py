import json
import os
import boto3
from datetime import datetime
from botocore.exceptions import ClientError


def get_sns_client():
    """Lazy-load SNS client with region from environment"""
    return boto3.client(
        "sns", region_name=os.environ.get("AWS_REGION", "eu-west-1")
    )


def get_s3_client():
    """Lazy-load S3 client with region from environment"""
    return boto3.client(
        "s3", region_name=os.environ.get("AWS_REGION", "eu-west-1")
    )


def get_ce_client():
    """Lazy-load Cost Explorer client with region from environment"""
    return boto3.client(
        "ce", region_name=os.environ.get("AWS_REGION", "eu-west-1")
    )

# Données mock — utilisées quand MOCK_MODE=true
MOCK_DATA = {
    "total_cost": 850.00,
    "cost_by_resource": {
        "notebooks": 212.00,
        "training": 297.00,
        "endpoints": 170.00,
        "storage": 42.50,
        "other": 128.50,
    },
}


def generate_recommendations(cost_by_resource):
    """
    Génère les recommandations d'économies pour chaque ressource SageMaker.

    Args:
        cost_by_resource (dict): Dictionnaire des coûts par type de ressource

    Returns:
        list: Liste de dictionnaires contenant les recommandations avec fields:
            - type (str): Catégorie de ressource (Notebooks, Training, etc.)
            - cost (float): Coût mensuel actuel
            - savings (float): Montant des économies potentielles
            - savings_pct (int): Pourcentage d'économies
            - effort (str): Niveau d'effort déployé (Low, Medium, High)
            - priority (str): Priorité basée sur ROI (Critical, High, Medium)
    """
    recs = []

    # Règles d'optimisation : (clé, % savings, nom, seuil min $, effort, priority)
    rules = [
        ("notebooks", 0.75, "Notebooks", 20, "Low", "High"),
        ("training", 0.70, "Training", 50, "Medium", "Critical"),
        ("endpoints", 0.30, "Endpoints", 50, "Medium", "High"),
        ("storage", 0.75, "Storage", 10, "Low", "Medium"),
    ]

    for key, pct, name, seuil, effort, priority in rules:
        cost = cost_by_resource.get(key, 0)
        if cost > seuil:
            recs.append(
                {
                    "type": name,
                    "cost": cost,
                    "savings": round(cost * pct, 2),
                    "savings_pct": round(pct * 100),
                    "effort": effort,
                    "priority": priority,
                    "issue": get_optimization_issue(name),
                }
            )

    # Trier par ROI (priority-based sorting)
    priority_score = {"Critical": 1, "High": 2, "Medium": 3}
    recs.sort(key=lambda x: (priority_score.get(x["priority"], 99), -x["savings"]))

    return recs


def get_optimization_issue(resource_type):
    """Retourne la description de l'optimisation pour chaque type de ressource"""
    issues = {
        "Notebooks": "Enable auto-stop for idle notebooks (detect no activity per 24h)",
        "Training": "Use Spot instances for training jobs (70% cheaper)",
        "Endpoints": "Implement auto-scaling for endpoints with low off-hours traffic",
        "Storage": "Apply S3 Lifecycle policies to move old data to Glacier",
    }
    return issues.get(resource_type, "Review resource configuration")


def generate_markdown_report(total_cost, total_savings, savings_pct, recs, report_date):
    """
    Génère un rapport Markdown avec résumé exécutif et recommandations.

    Args:
        total_cost (float): Coût total mensuel
        total_savings (float): Économies totales identifiées
        savings_pct (float): Pourcentage d'économies
        recs (list): Liste des recommandations triées par priorité
        report_date (str): Date du rapport (YYYY-MM-DD)

    Returns:
        str: Rapport formaté en Markdown
    """
    markdown = f"""# ML Cost Analysis Report

**Generated:** {report_date}

## Executive Summary

| Metric | Value |
|--------|-------|
| **Total Monthly Spend** | ${total_cost:,.2f} |
| **Identified Savings** | ${total_savings:,.2f} |
| **Savings Potential** | **{savings_pct}%** |
| **Recommendations** | {len(recs)} items |

---

## Optimization Recommendations

| Category | Issue | Monthly Savings | Effort | Priority |
|----------|-------|-----------------|--------|----------|
"""

    for rec in recs:
        markdown += (
            f"| {rec['type']} | {rec['issue']} | "
            f"${rec['savings']:,.2f} | {rec['effort']} | {rec['priority']} |\n"
        )

    markdown += """
---

## Next Steps (Sorted by ROI)

"""

    for idx, rec in enumerate(recs, 1):
        markdown += f"{idx}. **{rec['type']}** - {rec['issue']}\n"
        markdown += f"   - Potential Savings: ${rec['savings']:,.2f}/month\n"
        markdown += f"   - Effort: {rec['effort']} | Priority: {rec['priority']}\n\n"

    return markdown


def save_json_report(
    bucket_name, total_cost, total_savings, savings_pct, recs, report_date
):
    """
    Sauvegarde un rapport JSON structuré en S3 avec schéma strict.

    JSON Schema:
    {
        "metadata": {
            "report_date": str (YYYY-MM-DD),
            "generated_at": str (ISO 8601),
            "version": str (semantic version)
        },
        "summary": {
            "total_monthly_spend": float,
            "identified_savings": float,
            "savings_percentage": float,
            "recommendation_count": int
        },
        "optimizations": [
            {
                "category": str,
                "issue": str,
                "monthly_savings": float,
                "effort": str,
                "priority": str
            }
        ]
    }

    Args:
        bucket_name (str): Nom du bucket S3
        total_cost (float): Coût total mensuel
        total_savings (float): Économies totales
        savings_pct (float): Pourcentage d'économies
        recs (list): Recommandations
        report_date (str): Date du rapport

    Returns:
        str: URL du fichier JSON en S3
    """
    try:
        now = (
            datetime.now(datetime.UTC)
            if hasattr(datetime, "UTC")
            else datetime.utcnow()
        )

        # Structured JSON with strict schema
        report_data = {
            "metadata": {
                "report_date": report_date,
                "generated_at": now.isoformat() + "Z"
                if not hasattr(datetime, "UTC")
                else now.isoformat(),
                "version": "1.0.0",
            },
            "summary": {
                "total_monthly_spend": float(total_cost),
                "identified_savings": float(total_savings),
                "savings_percentage": float(savings_pct),
                "recommendation_count": len(recs),
            },
            "optimizations": [
                {
                    "category": rec["type"],
                    "issue": rec["issue"],
                    "monthly_savings": float(rec["savings"]),
                    "effort": rec["effort"],
                    "priority": rec["priority"],
                }
                for rec in recs
            ],
        }

        # Upload to S3
        json_key = f"reports/report_{report_date}.json"
        get_s3_client().put_object(
            Bucket=bucket_name,
            Key=json_key,
            Body=json.dumps(report_data, indent=2),
            ContentType="application/json",
            ServerSideEncryption="AES256",
        )

        s3_url = f"s3://{bucket_name}/{json_key}"
        print(f"✅ JSON report saved: {s3_url}")
        return s3_url
    except ClientError as e:
        print(f"❌ Error saving JSON report to S3: {e}")
        raise


def save_markdown_report(bucket_name, markdown_content, report_date):
    """
    Sauvegarde le rapport Markdown en S3.

    Args:
        bucket_name (str): Nom du bucket S3
        markdown_content (str): Contenu du rapport en Markdown
        report_date (str): Date du rapport

    Returns:
        str: URL du fichier Markdown en S3
    """
    try:
        md_key = f"reports/report_{report_date}.md"
        get_s3_client().put_object(
            Bucket=bucket_name,
            Key=md_key,
            Body=markdown_content.encode("utf-8"),
            ContentType="text/markdown",
            ServerSideEncryption="AES256",
        )

        s3_url = f"s3://{bucket_name}/{md_key}"
        print(f"✅ Markdown report saved: {s3_url}")
        return s3_url
    except ClientError as e:
        print(f"❌ Error saving Markdown report to S3: {e}")
        raise


def send_sns_notification(
    sns_topic_arn, total_savings, savings_pct, recommendation_count, markdown_s3_url
):
    """
    Envoie une notification SNS avec un résumé des économies identifiées.
    Gère les erreurs gracieusement sans faire échouer la Lambda.

    Args:
        sns_topic_arn (str): ARN du topic SNS
        total_savings (float): Économies totales identifiées
        savings_pct (float): Pourcentage d'économies
        recommendation_count (int): Nombre de recommandations
        markdown_s3_url (str): URL du rapport Markdown en S3
    """
    try:
        message = (
            f"ML Cost Analysis — ${total_savings:,.2f} identified in savings "
            f"({savings_pct}%) across {recommendation_count} recommendations.\n\n"
            f"Full report: {markdown_s3_url}"
        )

        response = get_sns_client().publish(
            TopicArn=sns_topic_arn,
            Subject="ML Cost Analysis Report - Weekly Summary",
            Message=message,
        )

        print(f"✅ SNS notification sent: {response['MessageId']}")
        return response
    except ClientError as e:
        # Log error but don't fail Lambda execution
        print(f"⚠️  Warning: SNS notification failed (non-blocking): {e}")
        return None


def handler(event, context):
    """
    Main Lambda handler for ML cost analysis.

    Flow:
    1. Fetch cost data (mock or AWS APIs)
    2. Generate recommendations sorted by ROI
    3. Save JSON structured report to S3
    4. Save Markdown report to S3
    5. Send SNS notification (non-blocking)
    6. Return structured response
    """
    print("🚀 ML Cost Analysis - Starting")

    try:
        # Get environment variables
        report_bucket = os.environ.get("REPORT_BUCKET")
        sns_topic_arn = os.environ.get("SNS_TOPIC_ARN")
        mock_mode = os.environ.get("MOCK_MODE", "false").lower() == "true"

        if not report_bucket and not mock_mode:
            raise ValueError("REPORT_BUCKET environment variable not set")

        # Fetch cost data
        if mock_mode:
            print("📊 Using mock data (MOCK_MODE=true)")
            data = MOCK_DATA
        else:
            # TODO: Replace with real boto3 calls to Cost Explorer when configured
            print("📊 Using mock data (real AWS integration pending)")
            data = MOCK_DATA

        # Generate recommendations (sorted by ROI/Priority)
        recs = generate_recommendations(data["cost_by_resource"])
        total_cost = data["total_cost"]
        total_savings = sum(r["savings"] for r in recs)
        savings_pct = (
            round(total_savings / total_cost * 100, 1) if total_cost > 0 else 0.0
        )

        # Generate report date
        report_date = datetime.now().strftime("%Y-%m-%d")

        print(f"💰 Total Cost   : ${total_cost:,.2f}")
        print(f"💸 Total Savings: ${total_savings:,.2f}")
        print(f"📈 Savings %    : {savings_pct}%")
        print(f"📋 Recommendations: {len(recs)}")

        # Initialize report URLs (may not be set in mock mode)
        json_url = None
        markdown_url = None

        # 1. Save structured JSON report to S3 (skip in mock mode)
        if not mock_mode:
            json_url = save_json_report(
                report_bucket, total_cost, total_savings, savings_pct, recs, report_date
            )

            # 2. Generate and save Markdown report
            markdown_content = generate_markdown_report(
                total_cost, total_savings, savings_pct, recs, report_date
            )
            markdown_url = save_markdown_report(
                report_bucket, markdown_content, report_date
            )

            # 3. Send SNS notification (non-blocking - errors caught)
            if sns_topic_arn:
                send_sns_notification(
                    sns_topic_arn, total_savings, savings_pct, len(recs), markdown_url
                )
            else:
                print("⚠️  Warning: SNS_TOPIC_ARN not configured, skipping notification")
        else:
            print("⏭️  Skipping S3 uploads and SNS in MOCK_MODE")

        # Return success response
        response_data = {
            "success": True,
            "total_cost": total_cost,
            "potential_savings": round(total_savings, 2),
            "savings_pct": savings_pct,
            "recommendation_count": len(recs),
            "recommendations": recs,
        }

        if json_url or markdown_url:
            response_data["reports"] = {
                "json_url": json_url,
                "markdown_url": markdown_url,
            }

        return {"statusCode": 200, "body": json.dumps(response_data, indent=2)}

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"success": False, "error": str(e)}),
        }


if __name__ == "__main__":
    # Local test mode - only with MOCK_MODE
    os.environ["MOCK_MODE"] = "true"
    os.environ["REPORT_BUCKET"] = "test-bucket"  # Won't actually upload in mock mode

    result = handler({}, None)
    print("\n" + "=" * 60)
    print("LOCAL TEST OUTPUT")
    print("=" * 60)
    print(result["body"])
