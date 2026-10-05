#!/usr/bin/env bash
# Emit evidence manifest skeleton for #36 / #34. Does not invent green runs.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIN="$ROOT/release/sens-source.pin"
# shellcheck disable=SC1090
source <(grep -E '^[A-Z0-9_]+=' "$PIN")
repo_sha="$(git -C "$ROOT" rev-parse HEAD)"
date_utc="$(date -u +%Y-%m-%dT%H:%MZ)"
futhark_ver="unknown"
if [[ -x "$ROOT/.tools/bin/futhark" ]]; then
  futhark_ver="$("$ROOT/.tools/bin/futhark" --version 2>/dev/null | head -n1 || true)"
elif command -v futhark >/dev/null 2>&1; then
  futhark_ver="$(futhark --version 2>/dev/null | head -n1 || true)"
fi
cat <<EOF
repo_sha=$repo_sha
sens_pin=${SENS_COMMIT}
futhark_version=$futhark_ver
cuda_toolkit=12.6
device=GTX 1050 Ti
cpu_witness=
cuda_witness=
run_url=
date=$date_utc
# Fill cpu_witness/cuda_witness/run_url only after live green self-hosted runs.
# Empty fields => do not cut #34 tag.
EOF
