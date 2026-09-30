#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$REPO_ROOT/.local"
kubectl kustomize "$REPO_ROOT" > "$REPO_ROOT/.local/rendered.yaml"
"${PYTHON:-python3}" "$REPO_ROOT/ci/validate_manifests.py" "$REPO_ROOT/.local/rendered.yaml"
