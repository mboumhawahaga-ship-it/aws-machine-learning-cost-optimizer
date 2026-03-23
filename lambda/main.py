# ─────────────────────────────────────────────
# CI/CD Pipeline — ML Cost Optimizer
# Se déclenche sur chaque push et pull request
# ─────────────────────────────────────────────
name: CI Quality

on:
  push:
    branches: [main]
  pull_request:

jobs:

  # ── Job 1 : Qualité du code (lint) ──────────
  lint:
    name: Lint Python
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Installer flake8
        run: pip install flake8

      - name: Lancer le lint
        # On ignore E501 (lignes trop longues) pour ne pas bloquer sur les commentaires
        run: flake8 lambda/main.py --ignore=E501

  # ── Job 2 : Tests avec mock ─────────────────
  test:
    name:  Tests Mock
    runs-on: ubuntu-latest
    needs: lint  # Lance seulement si le lint passe
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Installer les dépendances
        run: pip install boto3 pytest

      - name: Lancer les tests avec pytest
        # MOCK_MODE=true → aucun appel AWS réel, pas besoin de credentials
        env:
          MOCK_MODE: "true"
        run: pytest lambda/test_main.py -v

  # ── Job 3 : Build + Deploy Terraform ────────
  deploy:
    name: Deploy via Terraform
    runs-on: ubuntu-latest
    needs: test  # Lance seulement si les tests passent
    # Ne se déclenche que sur un push sur main (pas sur les PR)
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Zipper le code Lambda
        # Terraform attend ../lambda/function.zip (défini dans main.tf)
        run: |
          cd lambda
          zip -r function.zip main.py requirements.txt
          echo " function.zip créé ($(du -sh function.zip | cut -f1))"

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.7.0"

      - name: Terraform Init
        working-directory: terraform
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_DEFAULT_REGION: eu-west-1
        run: terraform init

      - name: Terraform Plan
        working-directory: terraform
        env:
          AWS_ACCESS_KEY_ID=xxx
          AWS_SECRET_ACCESS_KEY=xxx

          AWS_DEFAULT_REGION: eu-west-1
        run: terraform plan

      - name: Terraform Apply
        working-directory: terraform
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_DEFAULT_REGION: eu-west-1
        run: terraform apply -auto-approve
