#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="${SCRIPT_DIR}/results"
mkdir -p "$RESULTS_DIR"

PROCUREMENT_URL="${PROCUREMENT_URL:-http://localhost:8001}"
INTEGRATIONS_URL="${INTEGRATIONS_URL:-http://localhost:8002}"

echo "=== Portfolio Load Test Suite ==="
echo "Procurement Platform: $PROCUREMENT_URL"
echo "Integrations Hub:     $INTEGRATIONS_URL"
echo ""

if ! command -v k6 &>/dev/null; then
  echo "ERROR: k6 is not installed."
  echo "Install it: https://grafana.com/docs/k6/latest/set-up/install-k6/"
  exit 1
fi

echo "--- Running procurement-platform load test ---"
k6 run \
  -e BASE_URL="$PROCUREMENT_URL" \
  --out json="$RESULTS_DIR/procurement-platform-raw.json" \
  "$SCRIPT_DIR/k6-procurement.js" \
  2>&1 | tee "$RESULTS_DIR/procurement-platform-output.txt"

echo ""
echo "--- Running integrations-hub load test ---"
k6 run \
  -e BASE_URL="$INTEGRATIONS_URL" \
  --out json="$RESULTS_DIR/integrations-hub-raw.json" \
  "$SCRIPT_DIR/k6-integrations.js" \
  2>&1 | tee "$RESULTS_DIR/integrations-hub-output.txt"

echo ""
echo "=== Load tests complete ==="
echo "Results saved to: $RESULTS_DIR/"
echo "Copy relevant numbers into PERF_REPORT.md"
