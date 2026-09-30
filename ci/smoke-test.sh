#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
"${PYTHON:-python3}" "$REPO_ROOT/ci/smoke_test.py" "$@"
