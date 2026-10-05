#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FUTHARK="${FUTHARK:-$ROOT/.tools/bin/futhark}"
OUT="$ROOT/build/smoke-opencl"
RESULT="$ROOT/build/smoke-opencl.out"

if [[ ! -x "$FUTHARK" ]]; then
  echo "Futhark compiler not found at $FUTHARK" >&2
  echo "Run tools/install-futhark.sh first." >&2
  exit 2
fi

mkdir -p "$ROOT/build"

echo "== compiler =="
"$FUTHARK" --version

echo "== compile OpenCL backend =="
"$FUTHARK" opencl "$ROOT/src/smoke.fut" -o "$OUT"

echo "== execute =="
printf '[1i32, 2i32, 3i32, 4i32]\n' | "$OUT" | tee "$RESULT"

if ! grep -Fq '[2i32, 3i32, 4i32, 5i32]' "$RESULT"; then
  echo "Unexpected smoke-test output." >&2
  exit 3
fi

echo "PASS: Futhark OpenCL smoke test"
