#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FUTHARK="${FUTHARK:-$ROOT/.tools/bin/futhark}"
OUT="$ROOT/build/smoke-cuda"
RESULT="$ROOT/build/smoke-cuda.out"
CUDA_ROOT="${CUDA_HOME:-${CUDA_PATH:-/usr/local/cuda-12.6}}"
CUDA_TARGET="$CUDA_ROOT/targets/x86_64-linux"

if [[ ! -x "$FUTHARK" ]]; then
  echo "Futhark compiler not found at $FUTHARK" >&2
  echo "Run tools/install-futhark.sh first." >&2
  exit 2
fi

if [[ ! -f "$CUDA_TARGET/include/cuda.h" ]]; then
  echo "cuda.h not found under $CUDA_TARGET/include" >&2
  exit 4
fi

export CPATH="$CUDA_TARGET/include${CPATH:+:$CPATH}"
export LIBRARY_PATH="/usr/lib/wsl/lib:$CUDA_TARGET/lib${LIBRARY_PATH:+:$LIBRARY_PATH}"
export LD_LIBRARY_PATH="/usr/lib/wsl/lib:$CUDA_TARGET/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

mkdir -p "$ROOT/build"

echo "== compiler =="
"$FUTHARK" --version

echo "== CUDA paths =="
echo "CUDA_ROOT=$CUDA_ROOT"
echo "CUDA_TARGET=$CUDA_TARGET"

echo "== compile CUDA backend =="
"$FUTHARK" cuda "$ROOT/src/smoke.fut" -o "$OUT"

echo "== execute on CUDA device =="
printf '[1i32, 2i32, 3i32, 4i32]\n' | "$OUT" | tee "$RESULT"

if ! grep -Fq '[2i32, 3i32, 4i32, 5i32]' "$RESULT"; then
  echo "Unexpected smoke-test output." >&2
  exit 3
fi

echo "PASS: Futhark CUDA smoke test"
