#!/usr/bin/env bash
# Canonical SENS release entrypoint (#39).
# Does NOT implement the language — only invokes pinned juv4uk/sens CLI.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIN="$ROOT/release/sens-source.pin"

if [[ ! -f "$PIN" ]]; then
  echo "fail-closed: missing $PIN" >&2
  exit 2
fi

# shellcheck disable=SC1090
source <(grep -E '^[A-Z0-9_]+=' "$PIN")

CHECKOUT="${SENS_CHECKOUT_PATH:-vendor/sens}"
CHECKOUT_ABS="$ROOT/$CHECKOUT"

if [[ ! -d "$CHECKOUT_ABS" ]]; then
  echo "fail-closed: SENS checkout missing at $CHECKOUT" >&2
  echo "clone pinned source:" >&2
  echo "  git clone --depth 1 ${SENS_REPOSITORY} $CHECKOUT && git -C $CHECKOUT fetch --depth 1 origin ${SENS_COMMIT} && git -C $CHECKOUT checkout ${SENS_COMMIT}" >&2
  exit 2
fi

if [[ ! -d "$CHECKOUT_ABS/.git" && ! -f "$CHECKOUT_ABS/.git" ]]; then
  echo "fail-closed: $CHECKOUT is not a git checkout" >&2
  exit 2
fi

actual="$(git -C "$CHECKOUT_ABS" rev-parse HEAD)"
if [[ "$actual" != "$SENS_COMMIT" ]]; then
  echo "fail-closed: $CHECKOUT is $actual; pin requires $SENS_COMMIT" >&2
  exit 1
fi

if ! command -v cargo >/dev/null 2>&1; then
  echo "fail-closed: cargo not found; install Rust toolchain to run pinned sens-cli" >&2
  exit 2
fi

# No argument transformation — pass through as-is.
cd "$CHECKOUT_ABS"
exec cargo run -q -p sens-cli -- "$@"
