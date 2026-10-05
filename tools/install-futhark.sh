#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/toolchain/futhark.env"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

VERSION="${FUTHARK_VERSION:-0.27.1}"
PLATFORM="${FUTHARK_PLATFORM:-linux-x86_64}"
RELEASE_BASE_URL="${FUTHARK_RELEASE_BASE_URL:-https://futhark-lang.org/releases}"
ARCHIVE_SHA256="${FUTHARK_ARCHIVE_SHA256:-}"

TOOLS="$ROOT/.tools"
PREFIX="$TOOLS/futhark-$VERSION"
BIN="$TOOLS/bin"
ARCHIVE="$TOOLS/futhark-$VERSION-$PLATFORM.tar.xz"
URL="$RELEASE_BASE_URL/futhark-$VERSION-$PLATFORM.tar.xz"

mkdir -p "$TOOLS" "$BIN"

if [[ ! -x "$PREFIX/bin/futhark" ]]; then
  echo "Downloading Futhark $VERSION from $URL"
  curl --fail --location --retry 5 --retry-all-errors --show-error "$URL" -o "$ARCHIVE"

  if [[ -n "$ARCHIVE_SHA256" ]]; then
    echo "$ARCHIVE_SHA256  $ARCHIVE" | sha256sum -c -
  else
    echo "FUTHARK_ARCHIVE_SHA256 is required for reproducible bootstrap" >&2
    exit 3
  fi

  rm -rf "$PREFIX"
  mkdir -p "$PREFIX"
  tar -xJf "$ARCHIVE" --strip-components=1 -C "$PREFIX"
fi

ln -sfn "$PREFIX/bin/futhark" "$BIN/futhark"
"$BIN/futhark" --version | grep -F "$VERSION"
printf 'FUTHARK=%s\n' "$BIN/futhark"
