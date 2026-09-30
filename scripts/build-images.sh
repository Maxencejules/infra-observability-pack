#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/common.sh"
case "${1:---fixtures}" in
  --fixtures)
    docker build -f "$REPO_ROOT/demo/Dockerfile" -t procurement-platform:local "$REPO_ROOT"
    docker tag procurement-platform:local integrations-hub:local
    echo "Built synthetic, in-memory HTTP fixtures; no application database or webhook worker."
    ;;
  --apps)
    : "${PROCUREMENT_PATH:?Set PROCUREMENT_PATH to your existing application checkout}"
    : "${INTEGRATIONS_PATH:?Set INTEGRATIONS_PATH to your existing application checkout}"
    docker build -t procurement-platform:local "$PROCUREMENT_PATH"
    docker build -t integrations-hub:local "$INTEGRATIONS_PATH"
    ;;
  *) echo "Usage: bash scripts/build-images.sh [--fixtures|--apps]" >&2; exit 1 ;;
esac
kind load docker-image procurement-platform:local integrations-hub:local --name "$CLUSTER_NAME"
mkdir -p "$REPO_ROOT/.local"
docker image inspect procurement-platform:local integrations-hub:local > "$REPO_ROOT/.local/images.json"
