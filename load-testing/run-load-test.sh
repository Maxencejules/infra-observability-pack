#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROFILE="${PROFILE:-smoke}"
OUTPUT_DIR="${OUTPUT_DIR:-$REPO_ROOT/.local/load-test}"
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"
printf '{}\n' > "$OUTPUT_DIR/k6-empty.json"
k6 version > "$OUTPUT_DIR/k6-version.txt"
date -u +%FT%TZ > "$OUTPUT_DIR/started-at.txt"
git -C "$REPO_ROOT" rev-parse HEAD > "$OUTPUT_DIR/source-head.txt"
STATUS=0
# Ignore inherited k6 output/cloud/config options in this child shell.
while IFS= read -r option; do unset "$option"; done < <(compgen -e | sed -n '/^K6_/p')
for service in procurement integrations; do
  if [[ "$service" == procurement ]]; then
    BASE_URL="${PROCUREMENT_URL:-http://127.0.0.1:8001}"
  else
    BASE_URL="${INTEGRATIONS_URL:-http://127.0.0.1:8002}"
  fi
  EXTRA=()
  if [[ "$service" == procurement && -n "${PROCUREMENT_TOKEN:-}" ]]; then
    # Do not persist the token to artifact metadata or logs.
    EXTRA=(-e "PROCUREMENT_TOKEN=$PROCUREMENT_TOKEN")
  fi
  k6 --config "$OUTPUT_DIR/k6-empty.json" run --no-usage-report --include-system-env-vars=false \
    -e "BASE_URL=$BASE_URL" -e "PROFILE=$PROFILE" -e "ITERATIONS=${ITERATIONS:-1}" "${EXTRA[@]}" \
    --out "json=$OUTPUT_DIR/$service.jsonl" "$REPO_ROOT/load-testing/k6-$service.js" \
    > "$OUTPUT_DIR/$service.log" 2>&1 || STATUS=1
  cat "$OUTPUT_DIR/$service.log"
done
date -u +%FT%TZ > "$OUTPUT_DIR/finished-at.txt"
exit "$STATUS"
