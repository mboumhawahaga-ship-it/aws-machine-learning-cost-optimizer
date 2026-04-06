# Action Lambda — exécutée uniquement après approbation humaine

import json
import os
from datetime import datetime, timezone

import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

logger = Logger(service="ml-cost-optimizer")


def get_sagemaker_client():
    return boto3.client(
        "sagemaker", region_name=os.environ.get("AWS_REGION", "eu-west-1")
    )


def stop_notebook(notebook_name):
    """
    Arrête un notebook SageMaker (stop uniquement, pas de suppression).

    Args:
        notebook_name (str): Nom du notebook à arrêter

    Returns:
        dict: Résultat de l'action avec statut et timestamp
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        get_sagemaker_client().stop_notebook_instance(
            NotebookInstanceName=notebook_name
        )
        logger.info(f"✅ [{timestamp}] Notebook arrêté : {notebook_name}")
        return {
            "resource": notebook_name,
            "action": "stop_notebook",
            "status": "success",
            "timestamp": timestamp,
        }
    except ClientError as e:
        logger.error(f"❌ [{timestamp}] Échec arrêt notebook {notebook_name} : {e}")
        return {
            "resource": notebook_name,
            "action": "stop_notebook",
            "status": "error",
            "error": str(e),
            "timestamp": timestamp,
        }


def delete_endpoint(endpoint_name):
    """
    Supprime un endpoint SageMaker inactif.

    Args:
        endpoint_name (str): Nom de l'endpoint à supprimer

    Returns:
        dict: Résultat de l'action avec statut et timestamp
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        get_sagemaker_client().delete_endpoint(EndpointName=endpoint_name)
        logger.info(f"✅ [{timestamp}] Endpoint supprimé : {endpoint_name}")
        return {
            "resource": endpoint_name,
            "action": "delete_endpoint",
            "status": "success",
            "timestamp": timestamp,
        }
    except ClientError as e:
        logger.error(
            f"❌ [{timestamp}] Échec suppression endpoint {endpoint_name} : {e}"
        )
        return {
            "resource": endpoint_name,
            "action": "delete_endpoint",
            "status": "error",
            "error": str(e),
            "timestamp": timestamp,
        }


def handler(event, context):
    """
    Point d'entrée Lambda — exécute une action sur une ressource SageMaker.

    Event attendu :
        {
            "action_type": "stop_notebook" | "delete_endpoint",
            "resource_name": "<nom de la ressource>"
        }
    """
    logger.info("🚀 Action Lambda - Démarrage")

    try:
        action_type = event.get("action_type")
        resource_name = event.get("resource_name")

        if not action_type or not resource_name:
            raise ValueError(
                "Les champs 'action_type' et 'resource_name' sont obligatoires"
            )

        if action_type == "stop_notebook":
            result = stop_notebook(resource_name)
        elif action_type == "delete_endpoint":
            result = delete_endpoint(resource_name)
        else:
            raise ValueError(
                f"action_type inconnu : '{action_type}'. Valeurs acceptées : stop_notebook, delete_endpoint"
            )

        return {"statusCode": 200, "body": json.dumps(result)}

    except Exception as e:
        logger.error(f"❌ Erreur fatale : {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"success": False, "error": str(e)}),
        }
