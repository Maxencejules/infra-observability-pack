#!/usr/bin/env bash
set -euo pipefail

PROCUREMENT_URL="${PROCUREMENT_URL:-http://localhost:8001}"
INTEGRATIONS_URL="${INTEGRATIONS_URL:-http://localhost:8002}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"

ERRORS=0
PASS=0

check() {
  local name="$1"
  local url="$2"
  local expected_status="${3:-200}"
  local body_check="${4:-}"

  echo -n "  $name ... "

  HTTP_CODE=$(curl -s -o /tmp/smoke_body -w "%{http_code}" --connect-timeout 5 --max-time 10 "$url" 2>/dev/null || echo "000")

  if [ "$HTTP_CODE" = "$expected_status" ]; then
    if [ -n "$body_check" ]; then
      if grep -q "$body_check" /tmp/smoke_body 2>/dev/null; then
        echo "PASS ($HTTP_CODE)"
        PASS=$((PASS + 1))
      else
        echo "FAIL (body mismatch, expected '$body_check')"
        ERRORS=$((ERRORS + 1))
      fi
    else
      echo "PASS ($HTTP_CODE)"
      PASS=$((PASS + 1))
    fi
  else
    echo "FAIL (got $HTTP_CODE, expected $expected_status)"
    ERRORS=$((ERRORS + 1))
  fi
}

echo "=== Smoke Tests ==="
echo ""

echo "Procurement Platform ($PROCUREMENT_URL):"
check "Health"   "$PROCUREMENT_URL/health"   "200" '"ok"'
check "GraphQL"  "$PROCUREMENT_URL/graphql"  "200"
check "Metrics"  "$PROCUREMENT_URL/metrics"  "200" "http_requests_total"

echo ""
echo "Integrations Hub ($INTEGRATIONS_URL):"
check "Health"   "$INTEGRATIONS_URL/health"   "200" '"ok"'
check "Metrics"  "$INTEGRATIONS_URL/metrics"  "200" "http_requests_total"

echo ""
echo "Prometheus ($PROMETHEUS_URL):"
check "Ready"    "$PROMETHEUS_URL/-/ready"    "200"
check "Targets"  "$PROMETHEUS_URL/api/v1/targets" "200" '"status":"success"'

echo ""
echo "Grafana ($GRAFANA_URL):"
check "Health"   "$GRAFANA_URL/api/health"   "200" '"ok"'

echo ""
echo "=== Results: $PASS passed, $ERRORS failed ==="

if [ "$ERRORS" -gt 0 ]; then
  exit 1
fi
