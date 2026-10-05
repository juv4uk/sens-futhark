#!/usr/bin/env python3
"""Fail-closed importer for a versioned SENS fixture bundle (#7)."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

SCHEMA = "sens-fixture-bundle/1"
SOURCE_REPOSITORY = "juv4uk/sens"
PAYLOAD_NAME = "identity_vectors.csv"
CSV_HEADER = ("domain", "width", "bits", "exact_text")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
SUPPORTED_CONTRACT_VERSIONS = ("11.6",)


class BundleError(ValueError):
    """The source bundle is not safe to admit into this backend."""


@dataclass(frozen=True)
class ImportResult:
    source_commit: str
    contract_version: str
    payload_sha256: str
    payload_path: Path


def _read_manifest(source: Path) -> dict[str, object]:
    try:
        value = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BundleError(f"cannot read manifest.json: {error}") from error
    if not isinstance(value, dict):
        raise BundleError("manifest.json must contain an object")
    return value


def _require_string(manifest: dict[str, object], field: str) -> str:
    value = manifest.get(field)
    if not isinstance(value, str) or not value:
        raise BundleError(f"manifest field {field!r} is required")
    return value


def _validate_manifest(manifest: dict[str, object]) -> tuple[str, str, str]:
    if _require_string(manifest, "schema") != SCHEMA:
        raise BundleError(f"unsupported fixture schema: {manifest.get('schema')!r}")
    if _require_string(manifest, "source_repository") != SOURCE_REPOSITORY:
        raise BundleError("fixture source_repository is not juv4uk/sens")
    source_commit = _require_string(manifest, "source_commit")
    if not COMMIT_RE.fullmatch(source_commit):
        raise BundleError("source_commit must be a lowercase 40-hex Git SHA")
    contract_version = _require_string(manifest, "contract_version")
    if contract_version not in SUPPORTED_CONTRACT_VERSIONS:
        raise BundleError(f"unsupported contract_version: {contract_version!r}")
    if _require_string(manifest, "payload") != PAYLOAD_NAME:
        raise BundleError(f"schema v1 payload must be {PAYLOAD_NAME!r}")
    digest = _require_string(manifest, "payload_sha256")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise BundleError("payload_sha256 must be a lowercase SHA-256 hex digest")
    return source_commit, contract_version, digest


def _validate_payload(payload: Path, expected_digest: str) -> None:
    try:
        content = payload.read_bytes()
    except OSError as error:
        raise BundleError(f"cannot read fixture payload: {error}") from error
    if hashlib.sha256(content).hexdigest() != expected_digest:
        raise BundleError("fixture payload SHA-256 does not match manifest")
    try:
        rows = csv.DictReader(content.decode("utf-8").splitlines())
        if tuple(rows.fieldnames or ()) != CSV_HEADER:
            raise BundleError("fixture CSV header must be domain,width,bits,exact_text")
        identities: set[tuple[str, str]] = set()
        for number, row in enumerate(rows, start=2):
            if None in row.values() or any(row[name] is None for name in CSV_HEADER):
                raise BundleError(f"fixture CSV row {number} is malformed")
            identity = (row["domain"] or "", row["bits"] or "")
            if identity in identities:
                raise BundleError(f"fixture CSV row {number} duplicates identity {identity!r}")
            identities.add(identity)
    except UnicodeDecodeError as error:
        raise BundleError(f"fixture CSV is not UTF-8: {error}") from error


def _replace_directory(staged: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    backup = destination.with_name(f".{destination.name}.previous")
    if backup.exists():
        shutil.rmtree(backup)
    if destination.exists():
        os.replace(destination, backup)
    try:
        os.replace(staged, destination)
    except OSError:
        if backup.exists():
            os.replace(backup, destination)
        raise
    if backup.exists():
        shutil.rmtree(backup)


def import_bundle(source: Path, destination: Path) -> ImportResult:
    """Verify *source* fully, then replace *destination* with its admitted copy."""
    source = source.resolve()
    destination = destination.resolve()
    manifest = _read_manifest(source)
    source_commit, contract_version, digest = _validate_manifest(manifest)
    payload = source / PAYLOAD_NAME
    _validate_payload(payload, digest)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=f".{destination.name}.staged-", dir=destination.parent))
    try:
        shutil.copy2(source / "manifest.json", staged / "manifest.json")
        shutil.copy2(payload, staged / PAYLOAD_NAME)
        _replace_directory(staged, destination)
    except Exception:
        if staged.exists():
            shutil.rmtree(staged)
        raise
    return ImportResult(source_commit, contract_version, digest, destination / PAYLOAD_NAME)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="directory containing manifest.json")
    parser.add_argument("--destination", type=Path, required=True, help="admitted fixture directory")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        result = import_bundle(args.source, args.destination)
    except BundleError as error:
        print(f"fixture import rejected: {error}", file=sys.stderr)
        return 1
    print(
        "(fixture-import"
        f" (source {SOURCE_REPOSITORY})"
        f" (commit {result.source_commit})"
        f" (contract {result.contract_version})"
        f" (sha256 {result.payload_sha256})"
        ")"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
