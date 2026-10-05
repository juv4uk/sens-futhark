"""Contract tests for the fail-closed SENS fixture importer (#7)."""

from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from host import import_sens_fixture


CSV_HEADER = ["domain", "width", "bits", "exact_text"]
ROWS = [["1", "1", "0", "0"], ["1", "1", "1", "1"], ["2", "2", "0", "00"]]


def write_bundle(root: Path, **overrides: object) -> Path:
    payload = root / "identity_vectors.csv"
    with payload.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(CSV_HEADER)
        writer.writerows(ROWS)
    manifest = {
        "schema": "sens-fixture-bundle/1",
        "source_repository": "juv4uk/sens",
        "source_commit": "a" * 40,
        "contract_version": "11.6",
        "payload": "identity_vectors.csv",
        "payload_sha256": hashlib.sha256(payload.read_bytes()).hexdigest(),
    }
    manifest.update(overrides)
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return payload


class ImportBundleTests(unittest.TestCase):
    """Each test names a defect that must stop fixture admission."""

    def test_accepts_complete_bundle_and_copies_verified_payload(self) -> None:
        """Removing provenance validation must reject this accepted bundle."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            destination = root / "destination"
            source.mkdir()
            payload = write_bundle(source)

            result = import_sens_fixture.import_bundle(source, destination)

            self.assertEqual(result.payload_sha256, hashlib.sha256(payload.read_bytes()).hexdigest())
            self.assertEqual((destination / "identity_vectors.csv").read_bytes(), payload.read_bytes())
            self.assertEqual(json.loads((destination / "manifest.json").read_text(encoding="utf-8"))["source_commit"], "a" * 40)

    def test_rejects_payload_whose_bytes_do_not_match_manifest_digest(self) -> None:
        """Accepting altered bytes would silently admit stale or tampered evidence."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            destination = root / "destination"
            source.mkdir()
            payload = write_bundle(source)
            payload.write_text(payload.read_text(encoding="utf-8") + "2,2,1,01\n", encoding="utf-8")

            with self.assertRaises(import_sens_fixture.BundleError, msg="digest mismatch must fail closed"):
                import_sens_fixture.import_bundle(source, destination)
            self.assertFalse(destination.exists())

    def test_rejects_unknown_schema(self) -> None:
        """An unsupported schema must not be parsed by wishful compatibility."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            write_bundle(source, schema="sens-fixture-bundle/2")

            with self.assertRaises(import_sens_fixture.BundleError):
                import_sens_fixture.import_bundle(source, root / "destination")

    def test_rejects_non_sens_source_repository(self) -> None:
        """A similarly shaped bundle from another repository is not canonical SENS input."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            write_bundle(source, source_repository="example/not-sens")

            with self.assertRaises(import_sens_fixture.BundleError):
                import_sens_fixture.import_bundle(source, root / "destination")

    def test_rejects_missing_required_provenance(self) -> None:
        """Missing contract provenance must not turn into an unlabelled fixture copy."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            write_bundle(source)
            manifest_path = source / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            del manifest["contract_version"]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaises(import_sens_fixture.BundleError):
                import_sens_fixture.import_bundle(source, root / "destination")

    def test_rejects_duplicate_domain_bit_identity(self) -> None:
        """Duplicate exact identities make a witness corpus ambiguous."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            payload = write_bundle(source)
            with payload.open("a", encoding="utf-8", newline="") as handle:
                csv.writer(handle).writerow(ROWS[0])
            manifest_path = source / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["payload_sha256"] = hashlib.sha256(payload.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaises(import_sens_fixture.BundleError):
                import_sens_fixture.import_bundle(source, root / "destination")

    def test_rejects_csv_with_wrong_header(self) -> None:
        """A changed CSV shape must not be guessed into the old schema."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            payload = write_bundle(source)
            payload.write_text("domain,bits\n1,0\n", encoding="utf-8")
            manifest_path = source / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["payload_sha256"] = hashlib.sha256(payload.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaises(import_sens_fixture.BundleError):
                import_sens_fixture.import_bundle(source, root / "destination")


if __name__ == "__main__":
    unittest.main()
