# Action Lambda — exécutée uniquement après approbation humaine

import json
import os
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError


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
        print(f"✅ [{timestamp}] Notebook arrêté : {notebook_name}")
        return {
            "resource": notebook_name,
            "action": "stop_notebook",
            "status": "success",
            "timestamp": timestamp,
        }
    except ClientError as e:
        print(f"❌ [{timestamp}] Échec arrêt notebook {notebook_name} : {e}")
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
        print(f"✅ [{timestamp}] Endpoint supprimé : {endpoint_name}")
        return {
            "resource": endpoint_name,
            "action": "delete_endpoint",
            "status": "success",
            "timestamp": timestamp,
        }
    except ClientError as e:
        print(f"❌ [{timestamp}] Échec suppression endpoint {endpoint_name} : {e}")
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
    print("🚀 Action Lambda - Démarrage")

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
        print(f"❌ Erreur fatale : {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"success": False, "error": str(e)}),
        }
