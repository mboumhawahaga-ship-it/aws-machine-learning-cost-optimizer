import os
from datetime import datetime, timezone

import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

logger = Logger(service="ml-cost-optimizer")


def get_sagemaker_client():
    """Connexion au service SageMaker"""
    return boto3.client(
        "sagemaker", region_name=os.environ.get("AWS_REGION", "eu-west-1")
    )


def get_cloudwatch_client():
    """Connexion à CloudWatch pour les métriques"""
    return boto3.client(
        "cloudwatch", region_name=os.environ.get("AWS_REGION", "eu-west-1")
    )


def scan_notebooks():
    """
    Liste tous les notebooks SageMaker avec leur statut,
    type d'instance et coût estimé.

    Returns:
        list: Liste de notebooks avec leurs infos
    """
    sm = get_sagemaker_client()
    notebooks = []

    try:
        response = sm.list_notebook_instances()

        for nb in response["NotebookInstances"]:
            instance_type = nb.get("InstanceType", "inconnu")
            notebooks.append(
                {
                    "name": nb["NotebookInstanceName"],
                    "status": nb["NotebookInstanceStatus"],
                    "instance_type": instance_type,
                    "last_modified": str(nb.get("LastModifiedTime", "")),
                    # InService = allumé et coûte de l'argent
                    "is_running": nb["NotebookInstanceStatus"] == "InService",
                    "carbon_footprint_kg_month": calculate_carbon_footprint(
                        instance_type
                    ),
                }
            )

        logger.info(f"✅ {len(notebooks)} notebooks trouvés")
        return notebooks

    except ClientError as e:
        logger.error(f"❌ Erreur scan notebooks : {e}")
        return []


def scan_endpoints():
    """
    Liste tous les endpoints SageMaker actifs.

    Returns:
        list: Liste des endpoints avec leur statut
    """
    sm = get_sagemaker_client()
    endpoints = []

    try:
        response = sm.list_endpoints()

        for ep in response["Endpoints"]:
            endpoints.append(
                {
                    "name": ep["EndpointName"],
                    "status": ep["EndpointStatus"],
                    "last_modified": str(ep.get("LastModifiedTime", "")),
                    "is_running": ep["EndpointStatus"] == "InService",
                }
            )

        logger.info(f"✅ {len(endpoints)} endpoints trouvés")
        return endpoints

    except ClientError as e:
        logger.error(f"❌ Erreur scan endpoints : {e}")
        return []


def scan_training_jobs():
    """
    Liste les training jobs récents (30 derniers jours).

    Returns:
        list: Liste des training jobs
    """
    sm = get_sagemaker_client()
    jobs = []

    try:
        response = sm.list_training_jobs(StatusEquals="Completed", MaxResults=50)

        for job in response["TrainingJobSummaries"]:
            jobs.append(
                {
                    "name": job["TrainingJobName"],
                    "status": job["TrainingJobStatus"],
                    "creation_time": str(job.get("CreationTime", "")),
                    "end_time": str(job.get("TrainingEndTime", "")),
                }
            )

        logger.info(f"✅ {len(jobs)} training jobs trouvés")
        return jobs

    except ClientError as e:
        logger.error(f"❌ Erreur scan training jobs : {e}")
        return []


def check_rgpd_compliance(resource_name, resource_type):
    """
    Vérifie la conformité RGPD basique d'une ressource.
    Retourne les alertes et le niveau de risque.

    Args:
        resource_name: Nom de la ressource
        resource_type: Type (notebook, endpoint, training)

    Returns:
        dict: Statut conformité et alertes
    """
    sm = get_sagemaker_client()
    alerts = []
    risk_level = "Low"

    try:
        # Vérifie les tags de la ressource
        arn = f"arn:aws:sagemaker:{os.environ.get('AWS_REGION', 'eu-west-1')}:::{resource_type}/{resource_name}"
        tags_response = sm.list_tags(ResourceArn=arn)
        tags = {t["Key"]: t["Value"] for t in tags_response.get("Tags", [])}

        # Vérifie les tags obligatoires RGPD
        if "owner" not in tags:
            alerts.append("⚠️ Tag 'owner' manquant → responsable inconnu")
            risk_level = "Medium"

        if "data-classification" not in tags:
            alerts.append(
                "⚠️ Tag 'data-classification' manquant → données non classifiées"
            )
            risk_level = "Medium"

        if "expiration-date" not in tags:
            alerts.append(
                "⚠️ Tag 'expiration-date' manquant → pas de durée de rétention"
            )
            risk_level = "High"

        if not alerts:
            alerts.append("✅ Tags RGPD conformes")

    except ClientError:
        alerts.append("⚠️ Impossible de vérifier les tags")
        risk_level = "Unknown"

    return {
        "resource": resource_name,
        "type": resource_type,
        "rgpd_risk": risk_level,
        "alerts": alerts,
    }


def _build_rgpd_compliance(notebooks, endpoints):
    """Calcule la conformité RGPD une seule fois et détermine le risque global."""
    nb_results = [
        check_rgpd_compliance(n["name"], "notebook-instance") for n in notebooks
    ]
    ep_results = [check_rgpd_compliance(e["name"], "endpoint") for e in endpoints]
    all_results = nb_results + ep_results

    if any(r["rgpd_risk"] == "High" for r in all_results):
        global_risk = "High"
    elif any(r["rgpd_risk"] == "Medium" for r in all_results):
        global_risk = "Medium"
    else:
        global_risk = "Low"

    return {
        "notebooks": nb_results,
        "endpoints": ep_results,
        "global_risk": global_risk,
    }


def calculate_carbon_footprint(instance_type):
    """
    Retourne une estimation de l'empreinte carbone en kg CO² par mois
    selon le type d'instance SageMaker.

    Args:
        instance_type (str): Type d'instance (ex: ml.t3.medium)

    Returns:
        float: Empreinte carbone estimée en kg/mois
    """
    carbon_map = {
        "ml.t3.medium": 2.5,
        "ml.t3.xlarge": 8.0,
        "ml.p3.2xlarge": 45.0,
        "ml.p3.8xlarge": 180.0,
    }
    return carbon_map.get(instance_type, 5.0)


def run_discovery():
    """
    Point d'entrée principal : scanne toutes les ressources
    SageMaker et retourne un rapport complet.

    Returns:
        dict: Rapport complet avec toutes les ressources
    """
    logger.info("🔍 Démarrage du scan SageMaker...")

    notebooks = scan_notebooks()
    endpoints = scan_endpoints()
    training_jobs = scan_training_jobs()

    # Ressources qui coûtent de l'argent en ce moment
    running_notebooks = [n for n in notebooks if n["is_running"]]
    running_endpoints = [e for e in endpoints if e["is_running"]]

    rapport = {
        "scan_date": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_notebooks": len(notebooks),
            "running_notebooks": len(running_notebooks),
            "total_endpoints": len(endpoints),
            "running_endpoints": len(running_endpoints),
            "total_training_jobs": len(training_jobs),
        },
        "notebooks": notebooks,
        "endpoints": endpoints,
        "training_jobs": training_jobs,
        "rgpd_compliance": _build_rgpd_compliance(notebooks, endpoints),
    }

    logger.info(
        f"📊 Scan terminé : {len(running_notebooks)} notebooks actifs, {len(running_endpoints)} endpoints actifs"
    )
    return rapport


if __name__ == "__main__":
    # Test local
    os.environ["AWS_REGION"] = "eu-west-1"
    result = run_discovery()
    import json

    print(json.dumps(result, indent=2, default=str))
