#!/usr/bin/env python3
"""Focused tests for the compiler-backend/v1 boundary."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALID = ROOT / "tests" / "compiler_backend_v1.json"
TOOL = ROOT / "host" / "compiler_backend_v1.py"


def run(path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), str(path), *extra],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> int:
    good = run(VALID, "--lower")
    if good.returncode != 0:
        print(good.stdout + good.stderr)
        return 1
    lowered = json.loads(good.stdout)
    assert lowered["entry"] == "lower_pair_construct"
    assert lowered["target"] == "futhark"

    source = json.loads(VALID.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "bad.json"

        stale = json.loads(json.dumps(source))
        stale["provenance"]["source_commit"] = "0" * 40
        path.write_text(json.dumps(stale), encoding="utf-8")
        result = run(path)
        assert result.returncode == 2
        assert "stale provenance" in result.stdout

        unsupported = json.loads(json.dumps(source))
        unsupported["role"] = "QuoteForm"
        path.write_text(json.dumps(unsupported), encoding="utf-8")
        result = run(path, "--lower")
        assert result.returncode == 2
        assert "BLOCKED-MECHANISM" in result.stdout

        cpu = json.loads(json.dumps(source))
        cpu["admission"]["gpu"] = False
        path.write_text(json.dumps(cpu), encoding="utf-8")
        result = run(path)
        assert result.returncode == 2
        assert "GPU admission" in result.stdout

    print("compiler-backend/v1: ALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
