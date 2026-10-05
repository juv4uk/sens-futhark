"""Static contract tests for the managed sens-futhark runner lifecycle."""

from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
UNIT = ROOT / "systemd" / "actions-runner-sens-futhark.service"
TOOL = ROOT / "tools" / "runner-service.sh"


class RunnerServiceTests(unittest.TestCase):
    def test_unit_is_repo_scoped_and_restartable(self) -> None:
        text = UNIT.read_text(encoding="utf-8")
        self.assertIn("WorkingDirectory=%h/gpu-runners/sens-futhark", text)
        self.assertIn("ExecStart=%h/gpu-runners/sens-futhark/run.sh", text)
        self.assertIn("Restart=always", text)
        self.assertIn("KillSignal=SIGINT", text)
        self.assertIn("network-online.target", text)
        self.assertIn("ConditionFileIsExecutable=%h/gpu-runners/sens-futhark/run.sh", text)

    def test_unit_does_not_embed_credentials_or_registration_tokens(self) -> None:
        lowered = UNIT.read_text(encoding="utf-8").lower()
        for forbidden in ("registration-token", "github_token=", "pat=", "ghp_", "github_pat_"):
            self.assertNotIn(forbidden, lowered)

    def test_tool_refuses_duplicate_manual_listener(self) -> None:
        text = TOOL.read_text(encoding="utf-8")
        self.assertIn("manual_listener_is_live", text)
        self.assertIn("REFUSE_DUPLICATE_LISTENER", text)
        self.assertNotIn("wsl --terminate", text)
        self.assertNotIn("wsl.exe --terminate", text)

    def test_tool_is_valid_bash(self) -> None:
        result = subprocess.run(
            ["bash", "-n", str(TOOL)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
