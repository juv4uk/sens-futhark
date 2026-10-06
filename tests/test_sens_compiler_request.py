#!/usr/bin/env python3
"""Tests for consuming the SENS-owned compiler-semantic request."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "tests" / "compiler_semantic_request.lisp"
VALID = ROOT / "tests" / "compiler_backend_v1.json"
TOOL = ROOT / "host" / "compiler_backend_v1.py"


def run_sens(path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--sens-request",
            str(path),
            *extra,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> int:
    good = run_sens(
        REQUEST,
        "--lower",
        "--gpu-mechanism",
        "futhark.structural.selector-head-v1",
    )
    if good.returncode != 0:
        print(good.stdout + good.stderr)
        return 1

    lowered = json.loads(good.stdout)
    assert lowered["entry"] == "lower_selector_head"
    assert lowered["target"] == "futhark"
    assert lowered["role"] == "SelectorHead"
    assert lowered["source_commit"] == "c3878ef2be03894a46bde8263f75138adf276798"
    assert lowered["fixture_id"] == "car-nested-pair"

    manual = json.loads(VALID.read_text(encoding="utf-8"))
    assert manual["role"] == lowered["role"], "canonical SENS role must match parity fixture"
    assert manual["provenance"]["source_commit"] == lowered["source_commit"]
    assert manual["provenance"]["role_authority_digest"] == lowered["role_authority_digest"]

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "bad.lisp"

        stale = REQUEST.read_text(encoding="utf-8").replace(
            "c3878ef2be03894a46bde8263f75138adf276798", "0" * 40
        )
        path.write_text(stale, encoding="utf-8")
        result = run_sens(path)
        assert result.returncode == 2
        assert "stale SENS source revision" in result.stdout

        stale_authority = REQUEST.read_text(encoding="utf-8").replace(
            "a4d914073bc1a26f3721d404ac74894b99fe057159da76346ad2092a771bdfc9",
            "0" * 64,
        )
        path.write_text(stale_authority, encoding="utf-8")
        result = run_sens(path)
        assert result.returncode == 2
        assert "stale SENS role authority digest" in result.stdout

        d8 = REQUEST.read_text(encoding="utf-8").replace(
            "(domain . D3) (bits . 100)", "(domain . D8) (bits . 00000000)"
        )
        path.write_text(d8, encoding="utf-8")
        result = run_sens(path)
        assert result.returncode == 2
        assert "D8" in result.stdout

    print("SENS compiler-semantic request: ALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
