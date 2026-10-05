import json
import logging
import os
import socketserver
import time
from pathlib import Path

import torch

HOST = "127.0.0.1"
PORT = int(os.environ.get("SENS_GPU_RUNNER_PORT", "8765"))
ROOT = Path(__file__).resolve().parent
LOG = ROOT / "runner.log"
PID = ROOT / "runner.pid"
MAX_ELEMENTS = int(os.environ.get("SENS_GPU_RUNNER_MAX_ELEMENTS", "1000000"))

logging.basicConfig(
    filename=LOG,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

if not torch.cuda.is_available():
    raise SystemExit("CUDA unavailable")

DEVICE = torch.device("cuda:0")
torch.cuda.set_device(DEVICE)
ANCHOR = torch.empty((1,), device=DEVICE)
PROPS = torch.cuda.get_device_properties(DEVICE)


def gpu_info():
    free_b, total_b = torch.cuda.mem_get_info(DEVICE)
    return {
        "name": PROPS.name,
        "capability": list(torch.cuda.get_device_capability(DEVICE)),
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "free_bytes": int(free_b),
        "total_bytes": int(total_b),
        "allocated_bytes": int(torch.cuda.memory_allocated(DEVICE)),
        "reserved_bytes": int(torch.cuda.memory_reserved(DEVICE)),
    }


def ensure_size(n):
    if n < 0 or n > MAX_ELEMENTS:
        raise ValueError(f"element count {n} exceeds limit {MAX_ELEMENTS}")


def timed_gpu(fn):
    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)
    start.record()
    value = fn()
    end.record()
    end.synchronize()
    return value, float(start.elapsed_time(end))


def tensor1(values):
    ensure_size(len(values))
    return torch.tensor(values, dtype=torch.float32, device=DEVICE)


def op_ping(_req):
    return {"ok": True, "kind": "pong", "gpu": gpu_info()}


def op_add(req):
    a = req.get("a", [])
    b = req.get("b", [])
    if len(a) != len(b):
        raise ValueError("a and b must have equal length")
    ta = tensor1(a)
    tb = tensor1(b)
    out, ms = timed_gpu(lambda: ta + tb)
    return {"ok": True, "elapsed_ms": ms, "result": out.cpu().tolist()}


def op_mul(req):
    a = req.get("a", [])
    b = req.get("b", [])
    if len(a) != len(b):
        raise ValueError("a and b must have equal length")
    ta = tensor1(a)
    tb = tensor1(b)
    out, ms = timed_gpu(lambda: ta * tb)
    return {"ok": True, "elapsed_ms": ms, "result": out.cpu().tolist()}


def op_sum(req):
    a = req.get("a", [])
    ta = tensor1(a)
    out, ms = timed_gpu(lambda: torch.sum(ta))
    return {"ok": True, "elapsed_ms": ms, "result": float(out.item())}


def op_matmul(req):
    a = req.get("a", [])
    b = req.get("b", [])
    if not a or not b:
        raise ValueError("a and b must be non-empty 2D arrays")
    rows_a, cols_a = len(a), len(a[0])
    rows_b, cols_b = len(b), len(b[0])
    if any(len(r) != cols_a for r in a) or any(len(r) != cols_b for r in b):
        raise ValueError("ragged matrix")
    if cols_a != rows_b:
        raise ValueError("matrix dimensions do not align")
    ensure_size(rows_a * cols_a)
    ensure_size(rows_b * cols_b)
    ta = torch.tensor(a, dtype=torch.float32, device=DEVICE)
    tb = torch.tensor(b, dtype=torch.float32, device=DEVICE)
    out, ms = timed_gpu(lambda: ta @ tb)
    return {"ok": True, "elapsed_ms": ms, "result": out.cpu().tolist()}


def op_benchmark(req):
    n = int(req.get("n", 1_000_000))
    iters = int(req.get("iters", 100))
    ensure_size(n)
    if iters < 1 or iters > 10000:
        raise ValueError("iters must be in 1..10000")
    a = torch.ones(n, dtype=torch.float32, device=DEVICE)
    b = torch.ones(n, dtype=torch.float32, device=DEVICE)
    for _ in range(5):
        a = a + b
    torch.cuda.synchronize()
    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)
    start.record()
    for _ in range(iters):
        a = a + b
    end.record()
    end.synchronize()
    ms = float(start.elapsed_time(end))
    return {
        "ok": True,
        "operation": "vector_add",
        "n": n,
        "iters": iters,
        "total_ms": ms,
        "per_iter_ms": ms / iters,
        "gpu": gpu_info(),
    }


OPS = {
    "ping": op_ping,
    "add": op_add,
    "mul": op_mul,
    "sum": op_sum,
    "matmul": op_matmul,
    "benchmark": op_benchmark,
}


def dispatch(req):
    op = req.get("op")
    if op not in OPS:
        raise ValueError(f"unsupported op: {op}")
    result = OPS[op](req)
    if "job_id" in req:
        result["job_id"] = req["job_id"]
    return result


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        if self.client_address[0] not in ("127.0.0.1", "::1"):
            return
        for line in self.rfile:
            started = time.time()
            try:
                req = json.loads(line.decode("utf-8"))
                result = dispatch(req)
            except Exception as exc:
                logging.exception("job failed")
                result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
            result["wall_ms"] = (time.time() - started) * 1000.0
            self.wfile.write((json.dumps(result, separators=(",", ":")) + "\n").encode("utf-8"))
            self.wfile.flush()


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    PID.write_text(str(os.getpid()), encoding="utf-8")
    logging.info("sens-gpu-runner start port=%s gpu=%s", PORT, gpu_info())
    try:
        with Server((HOST, PORT), Handler) as server:
            server.serve_forever(poll_interval=0.25)
    finally:
        try:
            PID.unlink()
        except FileNotFoundError:
            pass
        logging.info("sens-gpu-runner stopped")


if __name__ == "__main__":
    main()
