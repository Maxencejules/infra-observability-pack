#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="${CLUSTER_NAME:-portfolio}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Paths to source repos (override with env vars if needed)
PROCUREMENT_PATH="${PROCUREMENT_PATH:-$(cd "$REPO_ROOT/../procurement_platform" && pwd)}"
INTEGRATIONS_PATH="${INTEGRATIONS_PATH:-$(cd "$REPO_ROOT/../integrations_hub" && pwd)}"

echo "=== Building container images ==="
echo "Procurement Platform: $PROCUREMENT_PATH"
echo "Integrations Hub:     $INTEGRATIONS_PATH"

# --- Apply metrics patch to procurement_platform if not already applied ---
if ! grep -q "prometheus_client" "$PROCUREMENT_PATH/backend/requirements.txt" 2>/dev/null; then
  echo ""
  echo "Applying Prometheus metrics patch to procurement_platform..."
  echo "prometheus-client>=0.21,<1" >> "$PROCUREMENT_PATH/backend/requirements.txt"
  cp "$REPO_ROOT/patches/procurement-platform-metrics.py" "$PROCUREMENT_PATH/backend/app/metrics.py"

  # Patch main.py to import metrics
  if ! grep -q "PrometheusMiddleware" "$PROCUREMENT_PATH/backend/app/main.py"; then
    sed -i '/^from app.auth.jwt/a from app.metrics import metrics_endpoint, PrometheusMiddleware' \
      "$PROCUREMENT_PATH/backend/app/main.py"
    sed -i '/^app.add_middleware(/i app.add_middleware(PrometheusMiddleware)' \
      "$PROCUREMENT_PATH/backend/app/main.py"
    sed -i '/^app.include_router(graphql_router/a app.add_route("/metrics", metrics_endpoint)' \
      "$PROCUREMENT_PATH/backend/app/main.py"
  fi
  echo "Metrics patch applied."
fi

# --- Fix Dockerfile to not use --reload in production ---
PROCUREMENT_DOCKERFILE="$PROCUREMENT_PATH/backend/Dockerfile"
if grep -q "\-\-reload" "$PROCUREMENT_DOCKERFILE" 2>/dev/null; then
  echo "Fixing procurement Dockerfile (removing --reload)..."
  sed -i 's/--reload//' "$PROCUREMENT_DOCKERFILE"
fi

# --- Build images ---
echo ""
echo "Building procurement-platform:local..."
docker build -t procurement-platform:local "$PROCUREMENT_PATH/backend"

echo ""
echo "Building integrations-hub:local..."
docker build -t integrations-hub:local "$INTEGRATIONS_PATH"

# --- Load into cluster ---
echo ""
echo "Loading images into cluster..."

if command -v kind &>/dev/null && kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
  kind load docker-image procurement-platform:local --name "$CLUSTER_NAME"
  kind load docker-image integrations-hub:local --name "$CLUSTER_NAME"
  echo "Images loaded into kind cluster."
elif command -v minikube &>/dev/null; then
  # For minikube, use the minikube docker daemon
  eval "$(minikube -p "$CLUSTER_NAME" docker-env)"
  docker build -t procurement-platform:local "$PROCUREMENT_PATH/backend"
  docker build -t integrations-hub:local "$INTEGRATIONS_PATH"
  echo "Images built in minikube docker."
fi

echo ""
echo "Images ready. Next step: ./scripts/deploy-all.sh"
