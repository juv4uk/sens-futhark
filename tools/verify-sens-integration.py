#!/usr/bin/env python3
"""Fail-closed verification of the pinned SENS integration boundary."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess

LOCK = Path(__file__).resolve().parents[1] / "integration" / "sens-execution-conformance.lock"

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("utf-8")
    return hashlib.sha1(header + data).hexdigest()

def load_lock() -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in LOCK.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values

def fail(message: str) -> None:
    raise SystemExit(f"FAIL-CLOSED: {message}")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, required=True, help="local checkout of pinned juv4uk/sens")
    ap.add_argument("--root", type=Path, required=True, help="root containing the exported upstream artifacts")
    args = ap.parse_args()

    lock = load_lock()
    repo = args.repo.resolve()
    root = args.root.resolve()
    if not (repo / ".git").exists():
        fail(f"not a git checkout: {repo}")

    try:
        sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    except subprocess.CalledProcessError as exc:
        fail(f"cannot resolve upstream HEAD: {exc}")

    if sha != lock["SENS_COMMIT"]:
        fail(f"upstream commit mismatch: got {sha}, expected {lock[\"SENS_COMMIT\"]}")

    checked = 0
    for key, value in sorted(lock.items()):
        if not key.startswith("SENS_FILE_"):
            continue
        rel, expected = value.split("|", 1)
        path = root / rel
        if not path.is_file():
            fail(f"missing locked artifact: {rel}")
        actual = git_blob_sha(path)
        if actual != expected:
            fail(f"artifact SHA mismatch: {rel}: got {actual}, expected {expected}")
        checked += 1

    if lock.get("SENS_CONTRACT") != "11.6":
        fail("contract pin is not 11.6")
    if lock.get("SENS_EXECUTION_SCHEMA") != "sens-execution-conformance/v1":
        fail("execution schema pin mismatch")
    if lock.get("SENS_RESEARCH_DOMAINS") != "D8":
        fail("D8 research cut is missing")

    print(f"SENS-INTEGRATION: PASS (commit={sha}, artifacts={checked}, contract=11.6)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
