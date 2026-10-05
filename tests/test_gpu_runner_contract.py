from pathlib import Path
import ast
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "tools" / "gpu_runner" / "worker.py"
CLIENT = ROOT / "tools" / "gpu_runner" / "client.py"


class GpuRunnerContractTests(unittest.TestCase):
    def test_python_sources_parse(self):
        ast.parse(WORKER.read_text(encoding="utf-8"))
        ast.parse(CLIENT.read_text(encoding="utf-8"))

    def test_worker_is_localhost_only(self):
        text = WORKER.read_text(encoding="utf-8")
        self.assertIn('HOST = "127.0.0.1"', text)
        self.assertNotIn("0.0.0.0", text)

    def test_worker_has_allowlisted_ops(self):
        text = WORKER.read_text(encoding="utf-8")
        for op in ("ping", "add", "mul", "sum", "matmul", "benchmark"):
            self.assertIn(f'"{op}"', text)
        self.assertNotIn("eval(", text)
        self.assertNotIn("subprocess", text)
        self.assertNotIn("os.system", text)

    def test_worker_has_resource_limits(self):
        text = WORKER.read_text(encoding="utf-8")
        self.assertIn("MAX_ELEMENTS", text)
        self.assertIn("iters > 10000", text)


if __name__ == "__main__":
    unittest.main()
