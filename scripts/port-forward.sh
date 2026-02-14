#!/usr/bin/env bash
set -euo pipefail

echo "=== Starting port forwards ==="
echo ""
echo "Services will be available at:"
echo "  Procurement Platform : http://localhost:8001"
echo "  Integrations Hub     : http://localhost:8002"
echo "  Prometheus           : http://localhost:9090"
echo "  Grafana              : http://localhost:3000  (admin/admin)"
echo ""
echo "Press Ctrl+C to stop all port forwards."
echo ""

# Run port-forwards in background, collect PIDs for cleanup
PIDS=()

cleanup() {
  echo ""
  echo "Stopping port forwards..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  exit 0
}
trap cleanup INT TERM

kubectl -n portfolio port-forward svc/procurement-platform 8001:8000 &
PIDS+=($!)

kubectl -n portfolio port-forward svc/integrations-hub 8002:8000 &
PIDS+=($!)

kubectl -n portfolio port-forward svc/prometheus 9090:9090 &
PIDS+=($!)

kubectl -n portfolio port-forward svc/grafana 3000:3000 &
PIDS+=($!)

# Wait for all background jobs
wait
