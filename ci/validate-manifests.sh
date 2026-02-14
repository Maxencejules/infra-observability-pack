#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== Kubernetes Manifest Validation ==="

ERRORS=0

# Use kubectl dry-run to validate manifests
for dir in "$REPO_ROOT"/kubernetes/*/; do
  echo "Validating: $dir"
  for file in "$dir"*.yaml; do
    [ -f "$file" ] || continue
    if kubectl apply --dry-run=client -f "$file" > /dev/null 2>&1; then
      echo "  OK: $(basename "$file")"
    else
      echo "  FAIL: $(basename "$file")"
      kubectl apply --dry-run=client -f "$file" 2>&1 | sed 's/^/    /'
      ERRORS=$((ERRORS + 1))
    fi
  done
done

# Validate namespace
echo "Validating: namespace.yaml"
if kubectl apply --dry-run=client -f "$REPO_ROOT/kubernetes/namespace.yaml" > /dev/null 2>&1; then
  echo "  OK: namespace.yaml"
else
  echo "  FAIL: namespace.yaml"
  ERRORS=$((ERRORS + 1))
fi

# Validate observability manifests
for dir in "$REPO_ROOT"/observability/*/; do
  echo "Validating: $dir"
  for file in "$dir"*.yaml; do
    [ -f "$file" ] || continue
    if kubectl apply --dry-run=client -f "$file" > /dev/null 2>&1; then
      echo "  OK: $(basename "$file")"
    else
      echo "  FAIL: $(basename "$file")"
      kubectl apply --dry-run=client -f "$file" 2>&1 | sed 's/^/    /'
      ERRORS=$((ERRORS + 1))
    fi
  done
done

echo ""
if [ "$ERRORS" -gt 0 ]; then
  echo "Validation found $ERRORS error(s)."
  exit 1
fi

echo "All manifests are valid."
