#!/usr/bin/env python3
"""Export the locked SENS conformance artifacts into the backend work tree."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "integration" / "sens-execution-conformance.lock"

def lock_values() -> dict[str, str]:
    values = {}
    for raw in LOCK.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        values[k] = v
    return values

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, required=True, help="local checkout of juv4uk/sens")
    ap.add_argument("--destination", type=Path, default=ROOT / "integration" / "upstream")
    args = ap.parse_args()

    values = lock_values()
    repo = args.repo.resolve()
    dest = args.destination.resolve()
    try:
        sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"FAIL-CLOSED: cannot resolve upstream HEAD: {exc}")
    expected = values["SENS_COMMIT"]
    if sha != expected:
        raise SystemExit(f"FAIL-CLOSED: upstream commit mismatch: got {sha}, expected {expected}")

    manifest = []
    for key, value in sorted(values.items()):
        if not key.startswith("SENS_FILE_"):
            continue
        rel, expected_blob = value.split("|", 1)
        src = repo / rel
        if not src.is_file():
            raise SystemExit(f"FAIL-CLOSED: missing upstream artifact: {rel}")
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
        manifest.append(f"{rel}|{expected_blob}")

    (dest / "UPSTREAM_COMMIT").write_text(sha + "\n", encoding="utf-8")
    (dest / "MANIFEST").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    print(f"SENS-EXPORT: PASS (commit={sha}, artifacts={len(manifest)})")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
