#!/usr/bin/env python3
"""Verify the canonical SENS compiler-compilation-artifact/1 boundary."""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SENS_ROOT = ROOT / "vendor" / "sens"
FIXTURE = "nucleus-d3-100"
EXPECTED_COMMIT = "1869fd5e51f38565ca968abceaa4bc933ae7a114"

def main() -> int:
    sys.path.insert(0, str(ROOT / "host"))
    from sens_compiler_request import SensRequestError, load_sens_artifact, load_sens_request

    cargo = shutil.which("cargo")
    if cargo is None:
        fallback = Path.home() / ".cargo" / "bin" / "cargo"
        cargo = str(fallback) if fallback.is_file() else None
    if cargo is None:
        raise SystemExit("cargo is required for the pinned SENS artifact producer")

    result = subprocess.run(
        [cargo, "run", "--quiet", "-p", "xtask", "--", "compiler-export", "--artifact", "--fixture", FIXTURE],
        cwd=SENS_ROOT, text=True, capture_output=True, check=False,
    )
    if result.returncode != 0:
        print(result.stdout + result.stderr)
        return 1

    artifact_text = result.stdout.strip()
    if not artifact_text.startswith("(compilation-artifact"):
        print("artifact producer did not emit compilation-artifact/1")
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "artifact.lisp"
        path.write_text(artifact_text + "\n", encoding="utf-8")
        artifact = load_sens_artifact(path)
        request_text = artifact["semantic_request"]
        assert artifact["fixture_id"] == FIXTURE
        assert hashlib.sha256(request_text.encode("utf-8")).hexdigest() == artifact["semantic_request_sha256"]

        request_path = Path(tmp) / "request.lisp"
        request_path.write_text(request_text + "\n", encoding="utf-8")
        request = load_sens_request(request_path)
        assert request["provenance"]["source_commit"] == EXPECTED_COMMIT
        assert request["fixture_id"] == FIXTURE

        tampered = artifact_text.replace(artifact["semantic_request_sha256"], "0" * 64, 1)
        path.write_text(tampered + "\n", encoding="utf-8")
        try:
            load_sens_artifact(path)
        except SensRequestError as exc:
            assert "digest mismatch" in str(exc)
        else:
            raise AssertionError("tampered semantic request digest was accepted")

    print("SENS compiler-compilation-artifact/1: ALL OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
