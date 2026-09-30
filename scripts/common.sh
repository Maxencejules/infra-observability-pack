#!/usr/bin/env bash
# Every kubectl call uses this private kubeconfig and named kind context.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLUSTER_NAME="${CLUSTER_NAME:-portfolio-observability}"
if [[ ! "$CLUSTER_NAME" =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]] || (( ${#CLUSTER_NAME} > 63 )); then
  echo "CLUSTER_NAME must be a DNS label of at most 63 characters" >&2
  exit 1
fi
KUBECONFIG_PATH="${KUBECONFIG_PATH:-$REPO_ROOT/.local/kubeconfig}"
CONTEXT="kind-$CLUSTER_NAME"
# shellcheck disable=SC2034 # Used by scripts that source this file.
KUBE=(kubectl --kubeconfig "$KUBECONFIG_PATH" --context "$CONTEXT")
PYTHON="${PYTHON:-python3}"
