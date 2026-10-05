#!/usr/bin/env bash
# Byte-identical stdout/stderr/exit: wrapper vs direct cargo in vendor/sens (#39).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIN="$ROOT/release/sens-source.pin"
# shellcheck disable=SC1090
source <(grep -E '^[A-Z0-9_]+=' "$PIN")
CHECKOUT="$ROOT/${SENS_CHECKOUT_PATH:-vendor/sens}"

if [[ ! -d "$CHECKOUT/.git" && ! -f "$CHECKOUT/.git" ]]; then
  echo "skip: no pinned checkout at $CHECKOUT (pin-only environment)"
  exit 0
fi

actual="$(git -C "$CHECKOUT" rev-parse HEAD)"
if [[ "$actual" != "$SENS_COMMIT" ]]; then
  echo "fail-closed: checkout $actual != pin $SENS_COMMIT" >&2
  exit 1
fi

SMOKE="$ROOT/release/smoke/hello.lisp"
if [[ ! -f "$SMOKE" ]]; then
  echo "fail-closed: missing smoke program $SMOKE" >&2
  exit 2
fi

tdir="$(mktemp -d)"
trap 'rm -rf "$tdir"' EXIT

set +e
bash "$ROOT/tools/sens-cli.sh" "$SMOKE" >"$tdir/w.out" 2>"$tdir/w.err"
w_code=$?
(cd "$CHECKOUT" && cargo run -q -p sens-cli -- "$SMOKE") >"$tdir/d.out" 2>"$tdir/d.err"
d_code=$?
set -e

if [[ "$w_code" != "$d_code" ]]; then
  echo "fail-closed: exit mismatch wrapper=$w_code direct=$d_code" >&2
  exit 1
fi
if ! cmp -s "$tdir/w.out" "$tdir/d.out"; then
  echo "fail-closed: stdout differs" >&2
  diff -u "$tdir/d.out" "$tdir/w.out" >&2 || true
  exit 1
fi
if ! cmp -s "$tdir/w.err" "$tdir/d.err"; then
  echo "fail-closed: stderr differs" >&2
  diff -u "$tdir/d.err" "$tdir/w.err" >&2 || true
  exit 1
fi

echo "(sens-cli-parity ok exit=$w_code commit=$SENS_COMMIT)"
