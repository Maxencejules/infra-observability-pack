#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
PIDS=()
cleanup() {
  for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
  for pid in "${PIDS[@]}"; do wait "$pid" 2>/dev/null || true; done
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
for mapping in 'procurement-platform 8001:8000' 'integrations-hub 8002:8000' 'prometheus 9090:9090' 'grafana 3000:3000'; do
  read -r service ports <<< "$mapping"
  "${KUBE[@]}" -n portfolio port-forward --address 127.0.0.1 "service/$service" "$ports" &
  PIDS+=("$!")
done
echo "Loopback ports: procurement 8001, integrations 8002, Prometheus 9090, Grafana 3000. Ctrl+C stops these forwards."
wait -n
