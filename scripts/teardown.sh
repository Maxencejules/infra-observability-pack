#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
if [[ "${1:-}" != --yes ]]; then
  read -r -p "Delete kind cluster '$CLUSTER_NAME' and its local data? Type the cluster name: " answer
  [[ "$answer" == "$CLUSTER_NAME" ]] || exit 1
fi
kind delete cluster --name "$CLUSTER_NAME"
