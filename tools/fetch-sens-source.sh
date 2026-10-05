#!/usr/bin/env bash
# Fetch the pinned canonical SENS source into the release checkout (#37).
#
# Goal: make "clone the release -> one command -> runs the real SENS language"
# actually work, so the parity smoke stops SKIPPING and really compares.
#
# Semantic authority stays juv4uk/sens. This script only *vendors* it at the
# pinned commit; it never copies or reimplements the language.
#
# Fail-closed: a missing/malformed pin, a clone failure, or any SHA mismatch
# stops the run. A stale or floating checkout is never accepted.
#
# Auth: juv4uk/sens is private, so the fetch needs a token. The token is taken
# from the environment (GH_TOKEN or GITHUB_TOKEN) and is NEVER hardcoded and
# NEVER written into the checkout's git config.
#
# Usage:
#   bash tools/fetch-sens-source.sh
#   make sens-fetch

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIN="$ROOT/release/sens-source.pin"

if [[ ! -f "$PIN" ]]; then
  echo "fail-closed: missing pin file $PIN" >&2
  exit 2
fi

# shellcheck disable=SC1090
source <(grep -E '^[A-Z0-9_]+=' "$PIN")

if [[ -z "${SENS_REPOSITORY:-}" || -z "${SENS_COMMIT:-}" ]]; then
  echo "fail-closed: pin missing SENS_REPOSITORY or SENS_COMMIT" >&2
  exit 2
fi
if [[ ! "$SENS_COMMIT" =~ ^[0-9a-f]{40}$ ]]; then
  echo "fail-closed: SENS_COMMIT must be a full 40-char SHA, got: $SENS_COMMIT" >&2
  exit 2
fi

CHECKOUT="${SENS_CHECKOUT_PATH:-vendor/sens}"
DEST="$ROOT/$CHECKOUT"

# Idempotent: already at the exact pin -> nothing to do.
if [[ -e "$DEST" ]]; then
  if [[ -d "$DEST/.git" || -f "$DEST/.git" ]]; then
    actual="$(git -C "$DEST" rev-parse HEAD 2>/dev/null || echo unknown)"
    if [[ "$actual" == "$SENS_COMMIT" ]]; then
      echo "(sens-source-fetch (checkout-ok $CHECKOUT@$actual))"
      exit 0
    fi
    echo "fail-closed: $CHECKOUT exists at $actual, pin requires $SENS_COMMIT" >&2
    echo "hint: remove it (rm -rf $CHECKOUT) and re-run; never silently float." >&2
    exit 1
  fi
  echo "fail-closed: $DEST exists but is not a git checkout" >&2
  exit 1
fi

TOKEN="${GH_TOKEN:-${GITHUB_TOKEN:-}}"

# Extra auth header, only for this fetch, only if a token is present. Passing it
# via -c keeps it OUT of the checkout's stored git config.
git_auth=()
if [[ -n "$TOKEN" ]]; then
  b64="$(printf 'x-access-token:%s' "$TOKEN" | base64 | tr -d '\n')"
  git_auth=(-c "http.extraheader=Authorization: Basic $b64")
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

mkdir -p "$(dirname "$DEST")"
echo "(sens-source-fetch: fetching $SENS_REPOSITORY @ $SENS_COMMIT)"
git -C "$tmp" init -q
git -C "$tmp" remote add origin "$SENS_REPOSITORY"   # tokenless URL on purpose

fetch_ok=0
# Preferred: fetch exactly the pinned commit, shallow.
if git -C "$tmp" "${git_auth[@]}" fetch -q --depth 1 origin "$SENS_COMMIT" 2>/dev/null; then
  fetch_ok=1
fi
# Fallback: some remotes refuse SHA-in-want; fetch the refs and check out the pin.
if [[ "$fetch_ok" -eq 0 ]]; then
  if ! git -C "$tmp" "${git_auth[@]}" fetch -q origin 2>/dev/null; then
    echo "fail-closed: could not fetch from $SENS_REPOSITORY." >&2
    echo "  juv4uk/sens is private: export GH_TOKEN or GITHUB_TOKEN with read access." >&2
    exit 1
  fi
fi

if ! git -C "$tmp" checkout -q "$SENS_COMMIT" 2>/dev/null; then
  echo "fail-closed: pin $SENS_COMMIT not found in $SENS_REPOSITORY" >&2
  exit 1
fi
got="$(git -C "$tmp" rev-parse HEAD)"
if [[ "$got" != "$SENS_COMMIT" ]]; then
  echo "fail-closed: checked out $got, pin requires $SENS_COMMIT" >&2
  exit 1
fi

mv "$tmp" "$DEST"
echo "(sens-source-fetch (checkout-ok $CHECKOUT@$got))"
