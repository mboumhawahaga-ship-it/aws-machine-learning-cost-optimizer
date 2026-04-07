# Rapport Optimisation SageMaker - eu-west-1

**Compte :** 384621379481  |  **Region :** eu-west-1  |  **Scan :** 2026-04-07 10:45 UTC

---

## Resume Executif

| Metrique | Valeur |
|----------|--------|
| Notebooks actifs | 0 / 0 total |
| Endpoints actifs | 0 / 0 total |
| Training Jobs (30j) | 0 |
| Studio Domains | 0 |
| Modeles enregistres | 0 |
| Pipelines | 0 |
| Feature Groups | 0 |
| Processing Jobs | 0 |
| AutoML Jobs | 0 |
| Depenses SageMaker (avril 2026) | $0.00 |
| Depenses SageMaker (3 mois hist.) | $0.00 |
| **Economies identifiees** | **$0.00** |

> **Conclusion :** Aucune ressource SageMaker deployee en eu-west-1. Compte sain - zero gaspillage detecte.

---

## Inventaire des Ressources

### Notebooks
| Nom | Statut | Instance | Modifie | CO2 kg/mois |
|-----|--------|----------|---------|-------------|
| *Aucun* | — | — | — | — |

### Endpoints
| Nom | Statut | Modifie | Actif |
|-----|--------|---------|-------|
| *Aucun* | — | — | — |

### Training Jobs (30 derniers jours)
| Nom | Statut | Debut | Fin |
|-----|--------|-------|-----|
| *Aucun* | — | — | — |

### Autres Ressources Scannees
| Type | Nombre |
|------|--------|
| Studio Domains | 0 |
| Modeles | 0 |
| Pipelines | 0 |
| Feature Groups | 0 |
| Processing Jobs | 0 |
| AutoML Jobs | 0 |
| Compilation Jobs | 0 |
| Experiments | 0 |
| Apps Studio | 0 |

---

## Conformite RGPD

**Risque global : Low**

| Ressource | Type | Risque | Alertes |
|-----------|------|--------|---------|
| *Aucune ressource a verifier* | — | LOW | Tags non applicables |

---

## Historique Couts SageMaker (Cost Explorer)

| Periode | Cout reel |
|---------|-----------|
| Janvier 2026 | $0.00 |
| Fevrier 2026 | $0.00 |
| Mars 2026 | $0.00 |
| Avril 2026 (en cours) | $0.00 |

---

## Recommandations Pre-Deploiement

Aucune ressource active, mais voici les regles a appliquer des le premier deploiement :

| Priorite | Categorie | Action | Economies potentielles | Effort |
|----------|-----------|--------|------------------------|--------|
| CRITICAL | Training Jobs | Spot Instances (70% moins cher) | Jusqu'a 70% | Medium |
| HIGH | Notebooks | Auto-stop apres 24h inactivite (CPU < 5%) | 75% du cout notebooks | Low |
| HIGH | Endpoints | Auto-scaling + scale-to-zero hors heures | 30% du cout endpoints | Medium |
| MEDIUM | Storage S3 | Lifecycle vers Glacier apres 90 jours | 83% stockage froid | Low |

### Plan d Action (avant premier deploiement)

1. **Tagging** - Appliquer owner / data-classification / expiration-date via Terraform
2. **Budget Alert** - AWS Budgets a $50/mois pour SageMaker
3. **Spot Training** - use_spot_instances=True + checkpoint S3
4. **Auto-stop Notebooks** - Lifecycle config : arret si CPU < 5% pendant 60 min
5. **Endpoint Scaling** - ScalingPolicy avec MinCapacity=0 pour endpoints non-RT
6. **S3 Lifecycle** - Transition vers Glacier automatique apres 90 jours

---

## Prochaines Etapes Infrastructure

- [ ] Deployer Step Functions + Lambda action (cf. lambda/action.py)
- [ ] Configurer EventBridge : scan hebdomadaire lundi 8h UTC
- [ ] Activer Cost Anomaly Detection pour SageMaker
- [ ] Mettre en place AWS Budgets avec alerte a $50

---

*Rapport genere par aws-machine-learning-cost-optimizer | Scan : 2026-04-07T10:45:55.987240+00:00*