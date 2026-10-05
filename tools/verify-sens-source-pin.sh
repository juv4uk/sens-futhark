#!/usr/bin/env bash
# Fail-closed verification of the canonical SENS source pin (#38).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIN="$ROOT/release/sens-source.pin"

if [[ ! -f "$PIN" ]]; then
  echo "fail-closed: missing pin file $PIN" >&2
  exit 2
fi

# shellcheck disable=SC1090
source <(grep -E '^[A-Z0-9_]+=' "$PIN")

if [[ -z "${SENS_COMMIT:-}" || -z "${SENS_REPOSITORY:-}" ]]; then
  echo "fail-closed: pin missing SENS_COMMIT or SENS_REPOSITORY" >&2
  exit 2
fi

if [[ ! "$SENS_COMMIT" =~ ^[0-9a-f]{40}$ ]]; then
  echo "fail-closed: SENS_COMMIT must be full 40-char SHA, got: $SENS_COMMIT" >&2
  exit 2
fi

echo "(sens-source-pin (repo $SENS_REPOSITORY) (commit $SENS_COMMIT) (contract ${SENS_CONTRACT:-unknown}))"

CHECKOUT="${SENS_CHECKOUT_PATH:-vendor/sens}"
CHECKOUT_ABS="$ROOT/$CHECKOUT"

if [[ ! -d "$CHECKOUT_ABS/.git" && ! -f "$CHECKOUT_ABS/.git" ]]; then
  echo "(sens-source-pin note: checkout absent at $CHECKOUT — pin file OK; runtime entrypoint requires clone)"
  exit 0
fi

actual="$(git -C "$CHECKOUT_ABS" rev-parse HEAD)"
if [[ "$actual" != "$SENS_COMMIT" ]]; then
  echo "fail-closed: checkout at $CHECKOUT is $actual, pin requires $SENS_COMMIT" >&2
  exit 1
fi

echo "(sens-source-pin checkout-ok $CHECKOUT@$actual)"
exit 0
