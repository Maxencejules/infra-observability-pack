#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
command -v kind >/dev/null
command -v kubectl >/dev/null
docker info >/dev/null
mkdir -p "$(dirname "$KUBECONFIG_PATH")"
if kind get clusters | grep -Fxq "$CLUSTER_NAME"; then
  kind export kubeconfig --name "$CLUSTER_NAME" --kubeconfig "$KUBECONFIG_PATH"
else
  kind create cluster --name "$CLUSTER_NAME" --kubeconfig "$KUBECONFIG_PATH" --wait 120s \
    --image kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5
fi
"${KUBE[@]}" cluster-info
