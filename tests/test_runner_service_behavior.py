"""Behavioral tests for tools/runner-service.sh (#69).

The existing tests/test_runner_service.py is a STATIC contract test: it asserts
the script *contains* certain strings. That cannot catch a behavioural
regression -- e.g. a doctor that keeps the "non-destructive" strings but starts
ignoring a live manual listener, or an install that proceeds despite one.

These tests exercise the doctor's actual BRANCHING with a stubbed `systemctl`
and a fake manual listener whose argv[0] contains the runner root (which is what
manual_listener_is_live matches), so the safety behaviour is checked, not just
its shape.

Nothing here touches a real runner: everything happens under a temp
SENS_FUTHARK_RUNNER_ROOT and a stub systemctl on PATH.
"""

import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "runner-service.sh"


class RunnerServiceBehaviorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="runner-service-test-")
        self.runner_root = Path(self.tmp) / "fakerunner"
        (self.runner_root / "_diag").mkdir(parents=True)
        (self.runner_root / ".runner").write_text("{}", encoding="utf-8")
        run_sh = self.runner_root / "run.sh"
        run_sh.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        run_sh.chmod(0o755)

        self.bin = Path(self.tmp) / "bin"
        self.bin.mkdir()
        stub = self.bin / "systemctl"
        stub.write_text(
            "#!/usr/bin/env bash\n"
            'verb=""; for a in "$@"; do case "$a" in --user) ;; *) verb="$a"; break;; esac; done\n'
            'case "$verb" in\n'
            "  show-environment) exit 0;;\n"
            '  is-active) [[ "${FAKE_ACTIVE:-0}" == "1" ]] && exit 0 || exit 3;;\n'
            "  *) exit 0;;\n"
            "esac\n",
            encoding="utf-8",
        )
        stub.chmod(0o755)

        self.env = dict(os.environ)
        self.env["SENS_FUTHARK_RUNNER_ROOT"] = str(self.runner_root)
        self.env["PATH"] = str(self.bin) + os.pathsep + self.env.get("PATH", "")
        self.listener = None

    def tearDown(self) -> None:
        if self.listener is not None:
            self.listener.terminate()
            try:
                self.listener.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.listener.kill()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_tool(self, *args: str, active: str = "0") -> subprocess.CompletedProcess:
        env = dict(self.env)
        env["FAKE_ACTIVE"] = active
        return subprocess.run(
            ["bash", str(TOOL), *args], capture_output=True, text=True, env=env, timeout=30
        )

    def start_fake_listener(self) -> None:
        # argv[0] contains the runner ROOT -- exactly what manual_listener_is_live matches.
        self.listener = subprocess.Popen(
            ["bash", "-c", 'exec -a "$SENS_FUTHARK_RUNNER_ROOT/run.sh" sleep 30'],
            env=self.env,
        )
        (self.runner_root / ".manual-runner.pid").write_text(str(self.listener.pid), encoding="utf-8")
        time.sleep(0.3)  # let the child settle so /proc/<pid>/cmdline is readable

    def test_doctor_no_listener_is_exit_4(self) -> None:
        result = self.run_tool("doctor", active="0")
        self.assertIn("DOCTOR=no-live-listener", result.stdout)
        self.assertEqual(result.returncode, 4)

    def test_doctor_live_manual_listener_is_exit_3(self) -> None:
        self.start_fake_listener()
        result = self.run_tool("doctor", active="0")
        self.assertIn("DOCTOR=manual-listener-live", result.stdout)
        self.assertEqual(result.returncode, 3)

    def test_doctor_duplicate_listeners_is_exit_5(self) -> None:
        self.start_fake_listener()
        result = self.run_tool("doctor", active="1")
        self.assertIn("DOCTOR=duplicate-listeners", result.stdout)
        self.assertEqual(result.returncode, 5)

    def test_install_refuses_duplicate_listener(self) -> None:
        self.start_fake_listener()
        result = self.run_tool("install", active="0")
        self.assertIn("REFUSE_DUPLICATE_LISTENER", result.stderr)
        self.assertEqual(result.returncode, 3)

    def test_doctor_ready_when_service_active_and_no_manual(self) -> None:
        result = self.run_tool("doctor", active="1")
        self.assertIn("DOCTOR=ready", result.stdout)
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
