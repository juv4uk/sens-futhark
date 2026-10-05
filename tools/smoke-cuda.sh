#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FUTHARK="${FUTHARK:-$ROOT/.tools/bin/futhark}"
OUT="$ROOT/build/smoke-cuda"
RESULT="$ROOT/build/smoke-cuda.out"

# shellcheck source=tools/cuda-env.sh
source "$ROOT/tools/cuda-env.sh"
cuda_env_require

if [[ ! -x "$FUTHARK" ]]; then
  echo "Futhark compiler not found at $FUTHARK" >&2
  echo "Run tools/install-futhark.sh first." >&2
  exit 2
fi

mkdir -p "$ROOT/build"

echo "== compiler =="
"$FUTHARK" --version

echo "== CUDA host capability =="
cuda_env_print
cuda_env_json

echo "== compile CUDA backend =="
"$FUTHARK" cuda "$ROOT/src/smoke.fut" -o "$OUT"

echo "== execute on CUDA device =="
printf '[1i32, 2i32, 3i32, 4i32]\n' | "$OUT" --entry-point add_one | tee "$RESULT"

if ! grep -Fq '[2i32, 3i32, 4i32, 5i32]' "$RESULT"; then
  echo "Unexpected smoke-test output." >&2
  exit 3
fi

echo "PASS: Futhark CUDA smoke test"
