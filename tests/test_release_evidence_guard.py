#!/usr/bin/env python3
"""Offline negative witnesses for release-evidence admission (no GitHub token)."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "release_evidence.py"
SPEC = importlib.util.spec_from_file_location("release_evidence", SCRIPT)
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)

SHA = "a" * 40
REPO = "juv4uk/sens-futhark"
RUN_ID = 123456
RUNNER = "GitHub Actions 100010"
JOB = {
    "name": "CUDA-only witness", "status": "completed", "conclusion": "success",
    "runner_name": RUNNER, "runner_group_name": "GitHub Actions",
    "labels": ["ubuntu-24.04"],
    "steps": [
        {"name": n, "conclusion": "success"} for n in (
            "Prove CUDA device contract",
            "Run CUDA-only workloads through CML admission",
            "Shared CUDA worker parity (CPU reference vs worker)",
            "Publish CUDA evidence metadata",
        )
    ],
}
RUN = {
    "id": RUN_ID, "head_sha": SHA, "head_branch": "main",
    "event": "push", "status": "completed", "conclusion": "success",
    "path": ".github/workflows/futhark.yml",
    "repository": {"full_name": REPO},
    "html_url": f"https://github.com/{REPO}/actions/runs/{RUN_ID}",
}
CAPABILITY = {
    "status": "ready", "device_visible": True, "header_present": True,
    "driver_present": True, "host_kind": "native-linux",
    "device_name": "NVIDIA TEST DEVICE", "driver_version": "TEST_DRIVER",
    "compute_capability": "8.0", "cuda_root": "/usr/local/cuda",
}
PARITY = {
    "schema": "gpu-worker-parity/1", "elements": 1048576,
    "chain": {"cuda_ns": 100}, "negative_control": "overflow rejected",
    "device": {"name": "NVIDIA TEST DEVICE"},
}


class EvidenceGuardTests(unittest.TestCase):
    def test_exact_valid_run(self):
        gate.validate_run(RUN, REPO, SHA, "futhark.yml", "main", RUN_ID)

    def test_wrong_sha_rejected(self):
        bad = dict(RUN, head_sha="b" * 40)
        with self.assertRaisesRegex(gate.EvidenceError, "RUN_SHA_MISMATCH"):
            gate.validate_run(bad, REPO, SHA, "futhark.yml", "main", RUN_ID)

    def test_wrong_branch_rejected(self):
        bad = dict(RUN, head_branch="feature")
        with self.assertRaisesRegex(gate.EvidenceError, "RUN_NOT_ON_RELEASE_BRANCH"):
            gate.validate_run(bad, REPO, SHA, "futhark.yml", "main", RUN_ID)

    def test_wrong_workflow_rejected(self):
        bad = dict(RUN, path=".github/workflows/hosted-runner-routing-policy.yml")
        with self.assertRaisesRegex(gate.EvidenceError, "RUN_WRONG_WORKFLOW"):
            gate.validate_run(bad, REPO, SHA, "futhark.yml", "main", RUN_ID)

    def test_successful_cuda_job(self):
        self.assertEqual(gate.validate_jobs([JOB]), JOB)

    def test_skipped_cuda_rejected(self):
        bad = dict(JOB, conclusion="skipped", runner_name=None)
        with self.assertRaisesRegex(gate.EvidenceError, "CUDA_SKIPPED_OR_FAILED"):
            gate.validate_jobs([bad])

    def test_local_runner_rejected(self):
        bad = dict(JOB, runner_name="wsm-i5-6400", runner_group_name="Default")
        with self.assertRaisesRegex(gate.EvidenceError, "CUDA_RUNNER_NOT_GITHUB_OWNED"):
            gate.validate_jobs([bad])

    def test_cuda_step_must_succeed(self):
        bad = copy.deepcopy(JOB)
        bad["steps"][1]["conclusion"] = "skipped"
        with self.assertRaisesRegex(gate.EvidenceError, "CUDA_STEP_NOT_SUCCESS"):
            gate.validate_jobs([bad])

    def make_artifacts(self, root, *, backend="cuda", environment="native-linux"):
        (root / "cuda.env").write_text(
            f"repository_sha={SHA}\nbackend={backend}\nrunner={RUNNER}\n"
            "policy=gpu-only\nfuthark_version=0.27.1\n"
            f"futhark_sha256={'b' * 64}\n", encoding="utf-8",
        )
        capability = dict(CAPABILITY, host_kind=environment)
        (root / "cuda-capability.json").write_text(
            json.dumps(capability), encoding="utf-8"
        )
        (root / "gpu-worker-parity.json").write_text(
            json.dumps(PARITY), encoding="utf-8"
        )

    def test_complete_hardware_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_artifacts(root)
            env, capability = gate.validate_artifact(root, SHA, RUN_ID, JOB)
            self.assertEqual(env["backend"], "cuda")
            self.assertEqual(capability["device_name"], "NVIDIA TEST DEVICE")

    def test_cpu_artifact_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_artifacts(root, backend="c")
            with self.assertRaisesRegex(gate.EvidenceError, "CUDA_BACKEND_NOT_ATTESTED"):
                gate.validate_artifact(root, SHA, RUN_ID, JOB)

    def test_historical_wsl_artifact_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_artifacts(root, environment="wsl2")
            with self.assertRaisesRegex(gate.EvidenceError, "CUDA_LOCAL_WSL_FORBIDDEN"):
                gate.validate_artifact(root, SHA, RUN_ID, JOB)

    def test_missing_parity_artifact_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_artifacts(root)
            (root / "gpu-worker-parity.json").unlink()
            with self.assertRaisesRegex(gate.EvidenceError, "ARTIFACT_MISSING_OR_DUPLICATED"):
                gate.validate_artifact(root, SHA, RUN_ID, JOB)

    def test_empty_cuda_timing_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_artifacts(root)
            bad = copy.deepcopy(PARITY)
            bad["chain"]["cuda_ns"] = 0
            (root / "gpu-worker-parity.json").write_text(
                json.dumps(bad), encoding="utf-8"
            )
            with self.assertRaisesRegex(gate.EvidenceError, "CUDA_NOT_EXECUTED"):
                gate.validate_artifact(root, SHA, RUN_ID, JOB)


if __name__ == "__main__":
    unittest.main()
