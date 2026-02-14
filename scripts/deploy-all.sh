#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== Deploying portfolio stack ==="

# --- Namespace ---
echo "Creating namespace..."
kubectl apply -f "$REPO_ROOT/kubernetes/namespace.yaml"

# --- PostgreSQL ---
echo "Deploying PostgreSQL..."
kubectl apply -f "$REPO_ROOT/kubernetes/postgres/"

echo "Waiting for PostgreSQL to be ready..."
kubectl -n portfolio rollout status statefulset/postgres --timeout=120s

# --- Application Services ---
echo "Deploying procurement-platform..."
kubectl apply -f "$REPO_ROOT/kubernetes/procurement-platform/"

echo "Deploying integrations-hub..."
kubectl apply -f "$REPO_ROOT/kubernetes/integrations-hub/"

# --- Observability ---
echo "Deploying Prometheus..."
kubectl apply -f "$REPO_ROOT/observability/prometheus/"

echo "Deploying Grafana..."
# Inject dashboard JSON into the ConfigMap
DASHBOARD_JSON=$(cat "$REPO_ROOT/observability/grafana/dashboard.json")
kubectl -n portfolio create configmap grafana-dashboards \
  --from-file=portfolio-overview.json="$REPO_ROOT/observability/grafana/dashboard.json" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -f "$REPO_ROOT/observability/grafana/datasource.yaml"
kubectl apply -f "$REPO_ROOT/observability/grafana/dashboard-provider.yaml"
kubectl apply -f "$REPO_ROOT/observability/grafana/deployment.yaml"
kubectl apply -f "$REPO_ROOT/observability/grafana/service.yaml"

# --- Wait for everything ---
echo ""
echo "Waiting for deployments to be ready..."
kubectl -n portfolio rollout status deployment/procurement-platform --timeout=120s
kubectl -n portfolio rollout status deployment/integrations-hub --timeout=120s
kubectl -n portfolio rollout status deployment/prometheus --timeout=60s
kubectl -n portfolio rollout status deployment/grafana --timeout=60s

echo ""
echo "=== All services deployed ==="
kubectl -n portfolio get pods
echo ""
echo "Next step: ./scripts/port-forward.sh"
