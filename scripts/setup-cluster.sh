#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="${CLUSTER_NAME:-portfolio}"

echo "=== Setting up local Kubernetes cluster ==="

# Detect available tool
if command -v kind &>/dev/null; then
  TOOL="kind"
elif command -v minikube &>/dev/null; then
  TOOL="minikube"
else
  echo "ERROR: Neither 'kind' nor 'minikube' found."
  echo ""
  echo "Install one of:"
  echo "  kind:     https://kind.sigs.k8s.io/docs/user/quick-start/#installation"
  echo "  minikube: https://minikube.sigs.k8s.io/docs/start/"
  exit 1
fi

echo "Using: $TOOL"

if [ "$TOOL" = "kind" ]; then
  # Check if cluster already exists
  if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
    echo "Cluster '$CLUSTER_NAME' already exists. Reusing."
  else
    echo "Creating kind cluster '$CLUSTER_NAME'..."
    kind create cluster --name "$CLUSTER_NAME" --wait 60s
  fi
  kubectl cluster-info --context "kind-${CLUSTER_NAME}"

elif [ "$TOOL" = "minikube" ]; then
  if minikube status -p "$CLUSTER_NAME" 2>/dev/null | grep -q "Running"; then
    echo "Cluster '$CLUSTER_NAME' already running. Reusing."
  else
    echo "Starting minikube cluster '$CLUSTER_NAME'..."
    minikube start -p "$CLUSTER_NAME" --memory 4096 --cpus 2 --wait all
  fi
  kubectl cluster-info
fi

echo ""
echo "Cluster is ready. Next step: ./scripts/build-images.sh"
