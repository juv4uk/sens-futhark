#!/usr/bin/env python3
"""Test the SENS-owned whole-program compiler-compilation-artifact/1 verifier."""
from __future__ import annotations

import hashlib
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "host"))

from sens_compiler_request import SensRequestError, load_sens_whole_program_artifact


PROGRAM_WIRE = b"SW\x01test\n"
PROGRAM_WIRE_SHA256 = "0724f53216b312098cb069e9363e824b89c0259a401d1d355a5bab9cd436fb68"
SEMANTIC_REQUESTS_SHA256 = "46f19a756a967ae8878275201153a52146e551b72c302607476934545ff13967"
SENS_REVISION = "5964c4dd2378364a5307b143a65438f8609fecd6"
AUTHORITY_SHA256 = (
    "9768f683e90cfb56ca95675d1f6ac0e6ede91e21cebe97e20b455cf1b3094791"
)
FIXTURE_NUCLEUS_SHA256 = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


def artifact_text() -> str:
    return f"""(compilation-artifact
  (schema . compiler-compilation-artifact/1)
  (artifact-kind . whole-program)
  (program-wire-sha256 . "{PROGRAM_WIRE_SHA256}")
  (semantic-requests-sha256 . "{SEMANTIC_REQUESTS_SHA256}")
  (authority-provenance . ("{SENS_REVISION}" "language-contract.lisp" "{AUTHORITY_SHA256}" "11.6" "{FIXTURE_NUCLEUS_SHA256}"))
  (semantic-requests . ((alpha)))
  (required-capabilities . ())
  (artifact-status . canonical-backend-neutral))
"""


def expect_failure(text: str, message: str, *, program_wire: bytes | None = PROGRAM_WIRE) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "artifact.lisp"
        path.write_text(text, encoding="utf-8")
        try:
            load_sens_whole_program_artifact(path, program_wire=program_wire)
        except SensRequestError as exc:
            assert message in str(exc), f"expected {message!r}, got {exc!r}"
        else:
            raise AssertionError(f"{message}: verifier accepted invalid artifact")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "artifact.lisp"
        path.write_text(artifact_text(), encoding="utf-8")
        artifact = load_sens_whole_program_artifact(path, program_wire=PROGRAM_WIRE)

        assert artifact["artifact_schema"] == "compiler-compilation-artifact/1"
        assert artifact["artifact_kind"] == "whole-program"
        assert artifact["program_wire_sha256"] == PROGRAM_WIRE_SHA256
        assert artifact["semantic_requests_sha256"] == SEMANTIC_REQUESTS_SHA256
        assert artifact["authority_provenance"]["sens_revision"] == SENS_REVISION
        assert artifact["authority_provenance"]["authority_path"] == "language-contract.lisp"
        assert artifact["artifact_status"] == "canonical-backend-neutral"

        expect_failure(
            artifact_text(),
            "program wire digest mismatch",
            program_wire=b"SW\x01tampered\n",
        )
        expect_failure(
            artifact_text().replace("(semantic-requests . ((alpha)))", "(semantic-requests . ((beta)))"),
            "semantic requests digest mismatch",
        )
        expect_failure(
            artifact_text().replace(
                "(semantic-requests-sha256 . \"" + SEMANTIC_REQUESTS_SHA256 + "\")",
                "(semantic-requests-sha256 . \"" + "0" * 64 + "\")",
            ),
            "semantic requests digest mismatch",
        )
        expect_failure(
            artifact_text().replace("(artifact-kind . whole-program)", "(artifact-kind . per-fixture)"),
            "whole-program",
        )
        expect_failure(
            artifact_text().replace(
                SENS_REVISION,
                "0" * 40,
                1,
            ),
            "stale SENS whole-program revision",
        )
        expect_failure(
            artifact_text().replace("(required-capabilities . ())", "(required-capabilities . (gpu))"),
            "capabilities must be empty",
        )
        expect_failure(
            artifact_text().replace(
                "(artifact-kind . whole-program)",
                "(artifact-kind . whole-program) (unexpected . field)",
                1,
            ),
            "field order/shape is not canonical",
        )

    expected_wire_hash = hashlib.sha256(PROGRAM_WIRE).hexdigest()
    assert expected_wire_hash == PROGRAM_WIRE_SHA256
    print("SENS whole-program compiler-compilation-artifact/1: ALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
