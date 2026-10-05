"""Public repository contracts for #7."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SENS_ROOT = Path("/home/agents/GitHub/sens")


class RepositorySurfaceTests(unittest.TestCase):
    def test_license_is_byte_identical_to_canonical_volnost(self) -> None:
        """Any edit to LICENSE would fork the canonical license text."""
        self.assertEqual((ROOT / "LICENSE").read_bytes(), (SENS_ROOT / "LICENSE").read_bytes())

    def test_readme_states_authority_and_opencl_limit_in_ukrainian(self) -> None:
        """Removing either boundary would let readers infer a false semantic or OpenCL claim."""
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("семантичною владою", readme)
        self.assertIn("OpenCL", readme)
        self.assertIn("відсутня", readme)

    def test_manifest_has_minimal_cpu_import_tools(self) -> None:
        """A pure Guix shell without one tool cannot reproduce import/witness work."""
        manifest = (ROOT / "manifest.scm").read_text(encoding="utf-8")
        for package in ('"python"', '"bash"', '"coreutils"', '"git"', '"nss-certs"'):
            self.assertIn(package, manifest)

    def test_guix_documentation_marks_cuda_as_optional_host_capability(self) -> None:
        """Calling CUDA guaranteed would turn an absent device into a false promise."""
        document = (ROOT / "guix/README.uk.md").read_text(encoding="utf-8")
        self.assertIn("host-provided", document)
        self.assertIn("optional", document)


if __name__ == "__main__":
    unittest.main()
