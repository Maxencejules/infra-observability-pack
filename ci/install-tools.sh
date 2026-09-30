#!/usr/bin/env bash
# Ubuntu amd64 CI only. SHA256 values from official release assets.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS="$REPO_ROOT/.local/tools"
mkdir -p "$TOOLS"
fetch() {
  curl --fail --location --retry 3 "$1" -o "$TOOLS/$2"
  printf '%s  %s\n' "$3" "$TOOLS/$2" | sha256sum --check
}
fetch https://github.com/prometheus/prometheus/releases/download/v3.13.3/prometheus-3.13.3.linux-amd64.tar.gz prometheus.tar.gz b349c732d8a853e657d0e7ae1bbad4d11b586615fb65fdc59d896b9f869c001e
fetch https://github.com/grafana/k6/releases/download/v2.3.0/k6-v2.3.0-linux-amd64.tar.gz k6.tar.gz 39c3117b6af817592dcd0ce4242105c0a7af10948c2a425306f0be8f7a8a8ab1
fetch https://github.com/kubernetes-sigs/kind/releases/download/v0.33.0/kind-linux-amd64 kind aee6151561422756b764a4ae28e7f44cda5af5a9eead3cc9985112b1de8d8e0d
tar -xzf "$TOOLS/prometheus.tar.gz" -C "$TOOLS"
tar -xzf "$TOOLS/k6.tar.gz" -C "$TOOLS"
chmod +x "$TOOLS/kind"
curl --fail --location --retry 3 https://dl.k8s.io/release/v1.37.0/bin/linux/amd64/kubectl -o "$TOOLS/kubectl"
curl --fail --location --retry 3 https://dl.k8s.io/release/v1.37.0/bin/linux/amd64/kubectl.sha256 -o "$TOOLS/kubectl.sha256"
printf '%s  %s\n' "$(cat "$TOOLS/kubectl.sha256")" "$TOOLS/kubectl" | sha256sum --check
chmod +x "$TOOLS/kubectl"
if [[ -n "${GITHUB_PATH:-}" ]]; then
  printf '%s\n' "$TOOLS" "$TOOLS/prometheus-3.13.3.linux-amd64" "$TOOLS/k6-v2.3.0-linux-amd64" >> "$GITHUB_PATH"
fi
