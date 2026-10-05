#!/usr/bin/env python3
"""Objective CPU↔CUDA benchmark harness for the merged exact-identity witness.

This file deliberately owns measurement only.  It does not define SENS semantics.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "futhark" / "identity_witness.fut"
DEFAULT_SIZES = [256, 1024, 4096, 16384, 65536, 262144, 1048576, 4194304]


def run(cmd, *, env=None, cwd=None, stdin=None, stdout=None, check=True, text=True):
    return subprocess.run(
        [str(x) for x in cmd],
        env=env,
        cwd=cwd,
        stdin=stdin,
        stdout=stdout,
        stderr=subprocess.PIPE if stdout is not None else subprocess.PIPE,
        check=check,
        text=text,
    )


def capture(cmd, *, env=None, cwd=None):
    p = subprocess.run(
        [str(x) for x in cmd],
        env=env,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return {"returncode": p.returncode, "output": p.stdout.strip()}


def find_futhark(explicit: str | None) -> Path:
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    if os.environ.get("FUTHARK"):
        candidates.append(Path(os.environ["FUTHARK"]))
    candidates.append(ROOT / ".tools" / "bin" / "futhark")
    found = shutil.which("futhark")
    if found:
        candidates.append(Path(found))
    for path in candidates:
        if path.is_file() and os.access(path, os.X_OK):
            return path.resolve()
    raise SystemExit("Futhark compiler not found. Set --futhark or FUTHARK.")


def cuda_env(base: dict[str, str]) -> dict[str, str]:
    env = dict(base)
    cuda_root = Path(env.get("CUDA_HOME") or env.get("CUDA_PATH") or "/usr/local/cuda-12.6")
    target = cuda_root / "targets" / "x86_64-linux"
    include = str(target / "include")
    lib = str(target / "lib")
    wsl = "/usr/lib/wsl/lib"

    def prepend(name: str, values: list[str]):
        old = env.get(name)
        env[name] = ":".join(values + ([old] if old else []))

    prepend("CPATH", [include])
    prepend("LIBRARY_PATH", [wsl, lib])
    prepend("LD_LIBRARY_PATH", [wsl, lib])
    env["CUDA_HOME"] = str(cuda_root)
    env["CUDA_PATH"] = str(cuda_root)
    return env


def timed(cmd, *, env, stdin_path: Path | None = None):
    start = time.perf_counter_ns()
    if stdin_path is None:
        p = subprocess.run(
            [str(x) for x in cmd],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=False,
        )
    else:
        with stdin_path.open("rb") as src:
            p = subprocess.run(
                [str(x) for x in cmd],
                env=env,
                stdin=src,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                check=False,
            )
    elapsed_ns = time.perf_counter_ns() - start
    if p.returncode != 0:
        sys.stderr.buffer.write(p.stderr)
        raise SystemExit(f"command failed ({p.returncode}): {' '.join(map(str, cmd))}")
    return elapsed_ns


def generate_dataset(futhark: Path, size: int, path: Path, env: dict[str, str]):
    # D7-valid workload: both arrays are full-width carriers for the already merged
    # validate_samples entry.  Domains are fixed to 7; bits are bounded 0..127.
    cmd = [
        futhark,
        "dataset",
        "--binary",
        "--i32-bounds=7:7",
        "-g",
        f"[{size}]i32",
        "--i32-bounds=0:127",
        "-g",
        f"[{size}]i32",
    ]
    with path.open("wb") as out:
        p = subprocess.run(cmd, env=env, stdout=out, stderr=subprocess.PIPE, check=False)
    if p.returncode != 0:
        sys.stderr.buffer.write(p.stderr)
        raise SystemExit(f"dataset generation failed for n={size}")


def compile_backend(futhark: Path, backend: str, exe: Path, env: dict[str, str]):
    start = time.perf_counter_ns()
    p = subprocess.run(
        [futhark, backend, PROGRAM, "-o", exe],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    elapsed_ns = time.perf_counter_ns() - start
    if p.returncode != 0:
        print(p.stdout, file=sys.stderr)
        raise SystemExit(f"{backend} compilation failed")
    return {"elapsed_ns": elapsed_ns, "log": p.stdout}


def bench_backend(
    futhark: Path,
    backend: str,
    spec: Path,
    out_json: Path,
    runs: int,
    env: dict[str, str],
    *,
    profile: bool,
):
    cmd = [
        futhark,
        "bench",
        PROGRAM,
        f"--backend={backend}",
        f"--spec-file={spec}",
        f"--runs={runs}",
        "--no-convergence-phase",
        f"--json={out_json}",
    ]
    if profile:
        cmd.append("--profile")
    p = subprocess.run(
        [str(x) for x in cmd],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    (out_json.parent / f"{backend}.bench.log").write_text(p.stdout)
    if p.returncode != 0:
        print(p.stdout, file=sys.stderr)
        raise SystemExit(f"futhark bench failed for backend={backend}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--futhark")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--sizes", default=",".join(map(str, DEFAULT_SIZES)))
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--cold-runs", type=int, default=5)
    args = ap.parse_args()

    sizes = [int(x) for x in args.sizes.split(",") if x]
    if len(sizes) < 1 or any(n <= 0 for n in sizes):
        raise SystemExit("sizes must contain positive integers")

    futhark = find_futhark(args.futhark)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = (args.out or ROOT / "bench" / "results" / stamp).resolve()
    data_dir = out / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    base_env = dict(os.environ)
    gpu_env = cuda_env(base_env)

    datasets = {}
    for n in sizes:
        path = data_dir / f"d7-valid-{n}.bin"
        generate_dataset(futhark, n, path, base_env)
        datasets[n] = path

    spec = out / "identity.spec"
    with spec.open("w", encoding="utf-8") as f:
        f.write("==\n")
        f.write("entry: validate_samples\n")
        for n in sizes:
            # Absolute paths make spec resolution independent of cwd.
            f.write(f'\"d7-valid-{n}\" input @ {datasets[n]}\n')

    exe_c = out / "identity-c"
    exe_cuda = out / "identity-cuda"
    compile_c = compile_backend(futhark, "c", exe_c, base_env)
    compile_cuda = compile_backend(futhark, "cuda", exe_cuda, gpu_env)

    cold_dataset = datasets[sizes[0]]
    cold = {"c": [], "cuda": []}
    for _ in range(args.cold_runs):
        cold["c"].append(
            timed([exe_c, "--entry-point", "validate_samples"], env=base_env, stdin_path=cold_dataset)
        )
        cold["cuda"].append(
            timed([exe_cuda, "--entry-point", "validate_samples"], env=gpu_env, stdin_path=cold_dataset)
        )

    c_json = out / "c.json"
    cuda_json = out / "cuda.json"
    bench_backend(futhark, "c", spec, c_json, args.runs, base_env, profile=False)
    bench_backend(futhark, "cuda", spec, cuda_json, args.runs, gpu_env, profile=True)

    # Human-readable profile reports retain kernel and host/device copy cost centres.
    p = subprocess.run(
        [futhark, "profile", cuda_json.name],
        cwd=out,
        env=gpu_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    (out / "cuda.profile.log").write_text(p.stdout)

    metadata = {
        "schema": 1,
        "timestamp_utc": stamp,
        "program": str(PROGRAM.relative_to(ROOT)),
        "git": capture(["git", "-C", ROOT, "rev-parse", "HEAD"])["output"],
        "futhark": capture([futhark, "--version"])["output"],
        "platform": platform.platform(),
        "sizes": sizes,
        "runs": args.runs,
        "cold_runs": args.cold_runs,
        "workload": {
            "name": "d7-valid",
            "domain": 7,
            "bits_bounds": [0, 127],
            "entry_point": "validate_samples",
        },
        "compile_ns": {
            "c": compile_c["elapsed_ns"],
            "cuda": compile_cuda["elapsed_ns"],
        },
        "cold_end_to_end_ns": cold,
        "cold_median_ns": {
            k: int(statistics.median(v)) for k, v in cold.items()
        },
        "nvidia_smi": capture(["nvidia-smi", "-L"]),
        "nvcc": capture(["nvcc", "--version"]),
        "raw": {
            "c_bench_json": c_json.name,
            "cuda_bench_json": cuda_json.name,
            "cuda_profile_dir": "cuda.prof",
        },
    }
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (out / "c.compile.log").write_text(compile_c["log"])
    (out / "cuda.compile.log").write_text(compile_cuda["log"])

    print(out)


if __name__ == "__main__":
    main()
