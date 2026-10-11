#!/usr/bin/env bash
# Release proof must come from a live GitHub Actions CUDA job, not from
# a green structural workflow or a local self-hosted artifact.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$ROOT/tools/release_evidence.py" "$@"
