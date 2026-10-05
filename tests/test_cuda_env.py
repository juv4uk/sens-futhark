"""Contract tests for the reusable CUDA host profile (#41)."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CUDA_ENV = ROOT / "tools" / "cuda-env.sh"


def run_cuda_env(*arguments: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        ["bash", str(CUDA_ENV), *arguments],
        cwd=ROOT,
        env=merged,
        text=True,
        capture_output=True,
        check=False,
    )


class CudaEnvTests(unittest.TestCase):
    def test_json_is_machine_readable_even_when_gpu_is_unavailable(self) -> None:
        result = run_cuda_env("json")
        self.assertEqual(result.returncode, 0, result.stderr)

        record = json.loads(result.stdout)
        for key in (
            "status",
            "host_kind",
            "cuda_root",
            "cuda_include",
            "cuda_toolkit_lib",
            "cuda_driver_lib",
            "header_present",
            "driver_present",
            "device_visible",
        ):
            self.assertIn(key, record)

    def test_explicit_host_paths_can_prove_a_ready_capability(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "cuda"
            target = root / "targets" / "x86_64-linux"
            include = target / "include"
            toolkit_lib = target / "lib"
            driver_lib = Path(directory) / "driver"
            fake_bin = Path(directory) / "bin"

            include.mkdir(parents=True)
            toolkit_lib.mkdir(parents=True)
            driver_lib.mkdir()
            fake_bin.mkdir()

            (include / "cuda.h").write_text("/* witness */\n", encoding="utf-8")
            (driver_lib / "libcuda.so.1").write_text("", encoding="utf-8")

            nvidia_smi = fake_bin / "nvidia-smi"
            nvidia_smi.write_text(
                "#!/usr/bin/env bash\n"
                "case \"$*\" in\n"
                "  *--query-gpu=name*) echo 'Synthetic GPU' ;;\n"
                "  *--query-gpu=driver_version*) echo '999.0' ;;\n"
                "  *--query-gpu=compute_cap*) echo '6.1' ;;\n"
                "  *) echo 'GPU 0: Synthetic GPU' ;;\n"
                "esac\n",
                encoding="utf-8",
            )
            nvidia_smi.chmod(nvidia_smi.stat().st_mode | stat.S_IXUSR)

            env = {
                "CUDA_HOME": str(root),
                "CUDA_PATH": str(root),
                "CUDA_DRIVER_LIB": str(driver_lib),
                "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}",
            }
            result = run_cuda_env("json", env=env)
            self.assertEqual(result.returncode, 0, result.stderr)

            record = json.loads(result.stdout)
            self.assertEqual(record["status"], "ready")
            self.assertEqual(record["cuda_root"], str(root))
            self.assertEqual(record["cuda_include"], str(include))
            self.assertEqual(record["cuda_toolkit_lib"], str(toolkit_lib))
            self.assertEqual(record["cuda_driver_lib"], str(driver_lib))
            self.assertTrue(record["header_present"])
            self.assertTrue(record["driver_present"])
            self.assertTrue(record["device_visible"])
            self.assertEqual(record["device_name"], "Synthetic GPU")

    def test_run_fails_closed_when_required_cuda_files_are_absent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing_root = Path(directory) / "missing-cuda"
            missing_driver = Path(directory) / "missing-driver"
            result = run_cuda_env(
                "run",
                "true",
                env={
                    "CUDA_HOME": str(missing_root),
                    "CUDA_PATH": str(missing_root),
                    "CUDA_DRIVER_LIB": str(missing_driver),
                },
            )

            self.assertEqual(result.returncode, 4)
            self.assertIn("CUDA host capability unavailable", result.stderr)
            self.assertIn("cuda.h", result.stderr)
            self.assertIn("libcuda", result.stderr)


if __name__ == "__main__":
    unittest.main()
