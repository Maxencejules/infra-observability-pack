#!/usr/bin/env bash
set -euo pipefail
CLUSTER_NAME="${CLUSTER_NAME:-portfolio-observability-proof}"
KUBECONFIG_PATH="${KUBECONFIG_PATH:-$(cd "$(dirname "$0")/.." && pwd)/.local/kind-proof/kubeconfig}"
source "$(dirname "$0")/../scripts/common.sh"
export CLUSTER_NAME KUBECONFIG_PATH
# Refuse reuse BEFORE enabling automatic cleanup. Interactive setup may reuse a cluster.
CLUSTERS="$(kind get clusters)"
if grep -Fxq "$CLUSTER_NAME" <<< "$CLUSTERS"; then
  echo "Proof requires a new cluster; '$CLUSTER_NAME' already exists." >&2
  exit 1
fi
CREATED=false
PIDS=()
cleanup() {
  if [[ "$CREATED" != true ]]; then return; fi
  mkdir -p "$REPO_ROOT/.local/kind-proof"
  "${KUBE[@]}" -n portfolio get pods -o json > "$REPO_ROOT/.local/kind-proof/final-pods.json" 2>/dev/null || true
  "${KUBE[@]}" -n portfolio get events > "$REPO_ROOT/.local/kind-proof/events.txt" 2>/dev/null || true
  for workload in prometheus grafana procurement-platform integrations-hub; do
    "${KUBE[@]}" -n portfolio logs "deployment/$workload" --all-containers > "$REPO_ROOT/.local/kind-proof/$workload.log" 2>&1 || true
  done
  for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true; done
  kind delete cluster --name "$CLUSTER_NAME"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
mkdir -p "$(dirname "$KUBECONFIG_PATH")"
docker info >/dev/null
# Direct creation: never use setup-cluster's reuse path in an automatic proof.
kind create cluster --name "$CLUSTER_NAME" --kubeconfig "$KUBECONFIG_PATH" --wait 120s \
  --image kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5
CREATED=true
"${KUBE[@]}" cluster-info
bash "$REPO_ROOT/scripts/build-images.sh" --fixtures
bash "$REPO_ROOT/scripts/deploy-all.sh"
# Separate forwards: killing an application pod must not stop the monitoring forwards.
for mapping in 'procurement-platform 8001:8000' 'integrations-hub 8002:8000' 'prometheus 9090:9090' 'grafana 3000:3000'; do
  read -r service ports <<< "$mapping"
  "${KUBE[@]}" -n portfolio port-forward --address 127.0.0.1 "service/$service" "$ports" > "$REPO_ROOT/.local/$service-forward.log" 2>&1 &
  PIDS+=("$!")
done
"$PYTHON" "$REPO_ROOT/ci/check_kind.py"
