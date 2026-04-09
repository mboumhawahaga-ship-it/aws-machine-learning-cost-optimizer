# Journal de bord

---

## Session — Avril 2026

### Ce qui fonctionne

- Scanner SageMaker : notebooks, Studio apps, endpoints, training jobs
- Rapports JSON + Markdown sauvegardés dans S3
- Notification email reçue dans Gmail
- 19/19 tests passent
- CI/CD GitHub Actions propre
- Infrastructure Terraform avec state S3 remote

---

### Erreurs rencontrées et solutions

**1. `POWERTOOLS_LOG_LEVEL=WARNING ` — espace parasite Windows**

```
ValueError: Unknown level: 'WARNING '
```

Sur Windows, `set VAR=valeur` ajoute parfois un espace invisible. Toujours utiliser `set "VAR=valeur"` avec les guillemets. Lambda Powertools est strict sur le format.

---

**2. Emojis dans les logs — encoding Windows cp1252**

```
UnicodeEncodeError: 'charmap' codec can't encode character
```

Le terminal Windows utilise cp1252 qui ne supporte pas les emojis. En prod Lambda c'est UTF-8 — aucun problème. En local : `set "PYTHONIOENCODING=utf-8"`.

---

**3. `detect-secrets` en boucle infinie**

Le hook recalculait les numéros de ligne à chaque commit, modifiait le baseline, ce qui déclenchait un nouveau cycle. Solution : `git commit --no-verify` uniquement pour le fichier baseline, jamais pour le code.

---

**4. ARN RGPD avec triple `:::`**

```python
# ❌
f"arn:aws:sagemaker:{region}:::{resource_type}/{resource_name}"
# ✅
f"arn:aws:sagemaker:{region}:{account_id}:{resource_type}/{resource_name}"
```

L'Account ID était absent. Tous les appels `list_tags()` échouaient silencieusement — la vérification RGPD ne fonctionnait jamais sans que personne ne s'en rende compte.

---

**5. `aws-lambda-powertools==3.9.1` — version inexistante**

Version épinglée qui n'existe pas sur PyPI. La liste saute de 3.9.0 à 3.10.0 directement. Corrigé en `3.27.0`.

---

**6. Test SNS qui échouait à cause de S3**

```
AssertionError: Lambda should return 200 even with SNS error
assert 500 == 200
```

Le test mockait SNS mais pas S3. Le handler faisait un vrai appel S3 → `AccessDenied` → crash avant d'atteindre le code SNS. Le test testait la mauvaise chose.

---

**7. Notebook SageMaker qui échouait au démarrage**

Le rôle Lambda n'a pas `sagemaker.amazonaws.com` comme principal — il ne peut pas être utilisé par SageMaker. Il faut un rôle dédié avec le bon `AssumeRolePolicy`.

---

**8. Gmail qui désabonnait automatiquement SNS**

Gmail détecte le mot "unsubscribe" dans les mails AWS et clique automatiquement dessus. Solution : marquer `no-reply@sns.amazonaws.com` comme contact, et chercher le mail de confirmation dans les spams.

---

### Leçon générale

La majorité des erreurs venaient de la différence entre l'environnement local Windows et Lambda — encoding, variables d'environnement, permissions IAM. En prod sur Lambda, aucun de ces problèmes n'existe. C'est pour ça que les tests avec moto sont importants : ils simulent Lambda sans dépendre de l'environnement local.

---

## À faire

- [ ] Cost Explorer réel — `GroupBy USAGE_TYPE` au lieu des pourcentages fixes (attendre 24h d'activation)
- [ ] CO2 dans les rapports — les données sont collectées mais pas incluses dans le Markdown
- [ ] Cache STS — `get_account_id()` appelle STS à chaque ressource, ajouter un cache module-level
