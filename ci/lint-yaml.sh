#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== YAML Lint ==="

if ! command -v yamllint &>/dev/null; then
  echo "Installing yamllint..."
  pip install --quiet yamllint
fi

ERRORS=0

# Lint all YAML files
find "$REPO_ROOT" \
  -name "*.yaml" -o -name "*.yml" \
  | grep -v node_modules \
  | grep -v .git \
  | while read -r file; do
    if ! yamllint -d "{extends: relaxed, rules: {line-length: {max: 150}}}" "$file" 2>/dev/null; then
      echo "FAIL: $file"
      ERRORS=$((ERRORS + 1))
    fi
  done

if [ "$ERRORS" -gt 0 ]; then
  echo ""
  echo "YAML lint found $ERRORS file(s) with issues."
  exit 1
fi

echo "All YAML files pass lint."
