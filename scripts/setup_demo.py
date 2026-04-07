import json
import os

import qrcode

# 1. Création de la structure des dossiers
path = "docs/samples"
if not os.path.exists(path):
    os.makedirs(path)
    print(f"Dossier {path} créé.")

# 2. Création d'un exemple de résultat (le 'Sample')
# C'est ce que ton outil est censé "produire" comme analyse
demo_results = {
    "project": "AWS ML Cost Optimizer",
    "scan_date": "2026-04-01",
    "recommendations": [
        {
            "resource_id": "notebook-instance-01",
            "current_type": "ml.t3.xlarge",
            "status": "Underutilized",
            "action": "Downsize to ml.t3.medium",
            "monthly_savings_est": "$45.00",
        },
        {
            "resource_id": "training-job-heavy-04",
            "current_type": "ml.p3.2xlarge",
            "status": "Complete",
            "action": "Use Spot Instances for next run",
            "monthly_savings_est": "$120.00",
        },
    ],
    "total_potential_savings": "$165.00",
}

with open(f"{path}/results_demo.json", "w") as f:
    json.dump(demo_results, indent=4, fp=f)
    print("Fichier results_demo.json généré.")

# 3. Génération du QR Code vers ton GitHub
github_url = (
    "https://github.com/mboumhawahaga-ship-it/aws-machine-learning-cost-optimizer"
)
qr_img = qrcode.make(github_url)
qr_img.save(f"{path}/github_qr_code.png")
print("QR Code généré : docs/samples/github_qr_code.png")
