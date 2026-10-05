#!/usr/bin/env bash
set -euo pipefail

VERSION="${FUTHARK_VERSION:-0.27.1}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS="$ROOT/.tools"
PREFIX="$TOOLS/futhark-$VERSION"
BIN="$TOOLS/bin"
ARCHIVE="$TOOLS/futhark-$VERSION-linux-x86_64.tar.xz"
URL="https://futhark-lang.org/releases/futhark-$VERSION-linux-x86_64.tar.xz"

mkdir -p "$TOOLS" "$BIN"

if [[ ! -x "$PREFIX/bin/futhark" ]]; then
  echo "Downloading Futhark $VERSION from $URL"
  curl --fail --location --retry 3 "$URL" -o "$ARCHIVE"
  rm -rf "$PREFIX"
  mkdir -p "$PREFIX"
  tar -xJf "$ARCHIVE" --strip-components=1 -C "$PREFIX"
fi

ln -sfn "$PREFIX/bin/futhark" "$BIN/futhark"
"$BIN/futhark" --version
printf 'FUTHARK=%s\n' "$BIN/futhark"
