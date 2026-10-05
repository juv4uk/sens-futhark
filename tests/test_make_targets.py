"""Black-box contract tests for #7 Make orchestration."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_make(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", *arguments], cwd=ROOT, text=True, capture_output=True, check=False
    )


class MakeTargetTests(unittest.TestCase):
    def test_import_fixture_without_explicit_source_fails_closed(self) -> None:
        """Dropping the source precondition must never select a local CSV fallback."""
        result = run_make("import-fixture")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SENS_FIXTURE_SOURCE", result.stdout + result.stderr)

    def test_parity_with_missing_runner_names_issue_18(self) -> None:
        """A missing comparison mechanism must be a named failure, not a pass."""
        result = run_make("witness-parity", "PARITY_RUNNER=/not/a/runner.py")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("#18", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
