#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
"${KUBE[@]}" apply -f "$REPO_ROOT/kubernetes/namespace.yaml"
"${KUBE[@]}" apply --dry-run=server -k "$REPO_ROOT"
"${KUBE[@]}" apply -k "$REPO_ROOT"
"${KUBE[@]}" -n portfolio rollout status statefulset/postgres --timeout=180s
for deployment in procurement-platform integrations-hub prometheus grafana; do
  "${KUBE[@]}" -n portfolio rollout status "deployment/$deployment" --timeout=180s
done
"${KUBE[@]}" -n portfolio get pods
