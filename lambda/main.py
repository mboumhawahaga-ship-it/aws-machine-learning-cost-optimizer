import json
import os

# Données mock — utilisées quand MOCK_MODE=true
MOCK_DATA = {
    "total_cost": 850.00,
    "cost_by_resource": {
        "notebooks": 212.00,
        "training": 297.00,
        "endpoints": 170.00,
        "storage": 42.50,
        "other": 128.50
    }
}


def generate_recommendations(cost_by_resource):
    """Génère les recommandations d'économies pour chaque ressource SageMaker"""
    recs = []

    rules = [
        ("notebooks", 0.75, "Notebooks",  20),
        ("training",  0.70, "Training",   50),
        ("endpoints", 0.30, "Endpoints",  50),
        ("storage",   0.75, "Storage",    10),
    ]

    for key, pct, name, seuil in rules:
        cost = cost_by_resource.get(key, 0)
        if cost > seuil:
            recs.append({
                "type": name,
                "cost": cost,
                "savings": round(cost * pct, 2),
                "savings_pct": round(pct * 100)
            })

    return recs


def handler(event, context):
    print("🚀 ML Cost Analysis")

    # MOCK_MODE=true → données simulées, pas d'appel AWS
    mock_mode = os.environ.get('MOCK_MODE', 'false').lower() == 'true'

    if mock_mode:
        data = MOCK_DATA
    else:
        # TODO: remplacer par les vrais appels boto3 quand AWS est configuré
        data = MOCK_DATA

    recs = generate_recommendations(data["cost_by_resource"])
    total_savings = sum(r["savings"] for r in recs)
    total_cost = data["total_cost"]

    # Protection contre la division par zéro
    savings_pct = round(total_savings / total_cost * 100, 1) if total_cost > 0 else 0.0

    print(f"💰 Coût total   : ${total_cost}")
    print(f"💸 Économies    : ${total_savings}")
    print(f"📋 Recommandations : {len(recs)}")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "success": True,
            "total_cost": total_cost,
            "potential_savings": round(total_savings, 2),
            "savings_pct": savings_pct,
            "recommendations": recs
        }, indent=2)
    }


if __name__ == "__main__":
    os.environ["MOCK_MODE"] = "true"
    result = handler({}, None)
    print(result["body"])
