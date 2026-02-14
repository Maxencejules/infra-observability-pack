#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="${CLUSTER_NAME:-portfolio}"

echo "=== Tearing down portfolio stack ==="

read -p "Delete the entire namespace and all data? [y/N] " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "Deleting namespace 'portfolio'..."
  kubectl delete namespace portfolio --ignore-not-found

  read -p "Also delete the local cluster? [y/N] " -n 1 -r
  echo ""
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    if command -v kind &>/dev/null && kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
      kind delete cluster --name "$CLUSTER_NAME"
      echo "Kind cluster deleted."
    elif command -v minikube &>/dev/null; then
      minikube delete -p "$CLUSTER_NAME"
      echo "Minikube cluster deleted."
    fi
  fi

  echo "Teardown complete."
else
  echo "Aborted."
fi
