# Makefile
# ---------
# Developer convenience targets for the AKS chatbot project.
# All commands assume you are in the repo root.

.PHONY: dev test lint build eval deploy-staging deploy-prod

# ── Local development ─────────────────────────────────────────────────────────
dev:
	@echo "Starting backend + frontend with docker compose..."
	docker compose up --build

# ── Tests ─────────────────────────────────────────────────────────────────────
test:
	pytest tests/ -v --tb=short

test-cov:
	pytest tests/ --cov=backend/app --cov-report=term-missing

# ── Linting & formatting ──────────────────────────────────────────────────────
lint:
	ruff check backend/
	ruff format --check backend/

lint-fix:
	ruff check --fix backend/
	ruff format backend/

# ── Docker build ──────────────────────────────────────────────────────────────
build:
	docker build -t chatbot/backend:local backend/
	docker build -t chatbot/frontend:local frontend/

# ── Evaluation gate ───────────────────────────────────────────────────────────
eval:
	python evaluation/run_eval.py --config agentops.yaml --output results.json

# ── Helm / AKS deploys ────────────────────────────────────────────────────────
CHART   = k8s/aks/chart
SECRETS = k8s/aks/chart/values-secrets.yaml

deploy-staging:
	helm upgrade --install chatbot-staging $(CHART) \
		--namespace staging --create-namespace \
		-f $(SECRETS) \
		--wait --timeout 5m

deploy-prod:
	helm upgrade --install chatbot $(CHART) \
		--namespace production --create-namespace \
		-f $(SECRETS) \
		--wait --timeout 10m
