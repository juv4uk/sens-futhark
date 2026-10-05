"""Black-box contract tests for #7 Make orchestration."""

from __future__ import annotations

import subprocess
import tempfile
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

    def test_imported_synthetic_fixture_emits_provenance_before_cpu_witness(self) -> None:
        """Removing provenance output would make a digest impossible to attribute."""
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "imported"
            imported = run_make(
                "import-fixture",
                f"SENS_FIXTURE_SOURCE={ROOT / 'fixtures/example'}",
                f"FIXTURE_DESTINATION={destination}",
            )
            self.assertEqual(imported.returncode, 0, imported.stderr)

            witness = run_make("witness-cpu", f"FIXTURE_DESTINATION={destination}")
            self.assertEqual(witness.returncode, 0, witness.stderr)
            self.assertIn("(provenance (source juv4uk/sens)", witness.stdout)
            self.assertIn("(commit aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa)", witness.stdout)
            self.assertIn("(contract 11.6)", witness.stdout)
            self.assertIn("(cpu-witness", witness.stdout)

    def test_parity_requires_explicit_backend_and_accepts_identical_cpu_witness(self) -> None:
        """Treating missing backend output as success would fabricate GPU parity."""
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "imported"
            imported = run_make(
                "import-fixture",
                f"SENS_FIXTURE_SOURCE={ROOT / 'fixtures/example'}",
                f"FIXTURE_DESTINATION={destination}",
            )
            self.assertEqual(imported.returncode, 0, imported.stderr)
            missing = run_make("witness-parity", f"FIXTURE_DESTINATION={destination}")
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("BACKEND_WITNESS", missing.stdout + missing.stderr)

            backend = Path(directory) / "backend.txt"
            backend.write_text(
                subprocess.run(
                    ["python3", "host/cpu_witness.py", "--fixture", str(destination / "identity_vectors.csv")],
                    cwd=ROOT, text=True, capture_output=True, check=True,
                ).stdout,
                encoding="utf-8",
            )
            parity = run_make(
                "witness-parity",
                f"FIXTURE_DESTINATION={destination}",
                f"BACKEND_WITNESS={backend}",
            )
            self.assertEqual(parity.returncode, 0, parity.stderr)
            self.assertIn("(parity", parity.stdout)


if __name__ == "__main__":
    unittest.main()
