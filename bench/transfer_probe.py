#!/usr/bin/env python3
"""Measure Futhark CUDA C-API import, kernel, and export phases separately."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "futhark" / "identity_witness.fut"
HARNESS = ROOT / "bench" / "transfer_probe.c"


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


def cuda_paths() -> tuple[Path, Path, Path]:
    root = Path(os.environ.get("CUDA_HOME") or os.environ.get("CUDA_PATH") or "/usr/local/cuda-12.6")
    target = root / "targets" / "x86_64-linux"
    driver = Path("/usr/lib/wsl/lib")
    header = target / "include" / "cuda.h"
    if not header.is_file():
        raise SystemExit(f"cuda.h not found: {header}")
    return root, target, driver


def run_checked(cmd: list[str | Path], *, env: dict[str, str] | None = None, capture: bool = False):
    p = subprocess.run(
        [str(x) for x in cmd],
        env=env,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if p.returncode != 0:
        if p.stdout:
            print(p.stdout, file=sys.stderr)
        if p.stderr:
            print(p.stderr, file=sys.stderr)
        raise SystemExit(f"command failed ({p.returncode}): {' '.join(map(str, cmd))}")
    return p


def median(values: list[int]) -> float:
    return float(statistics.median(values))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--futhark")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sizes", default="1048576,4194304,8388608")
    ap.add_argument("--repeats", type=int, default=5)
    args = ap.parse_args()

    sizes = [int(x) for x in args.sizes.split(",") if x]
    if not sizes or any(n <= 0 for n in sizes):
        raise SystemExit("sizes must contain positive integers")
    if args.repeats <= 0:
        raise SystemExit("repeats must be positive")

    futhark = find_futhark(args.futhark)
    cuda_root, cuda_target, driver = cuda_paths()
    out = args.out.resolve()
    build = out / "build"
    build.mkdir(parents=True, exist_ok=True)

    env = dict(os.environ)
    env["CUDA_HOME"] = str(cuda_root)
    env["CUDA_PATH"] = str(cuda_root)
    env["CPATH"] = f"{cuda_target / 'include'}" + (f":{env['CPATH']}" if env.get("CPATH") else "")
    env["LIBRARY_PATH"] = f"{driver}:{cuda_target / 'lib'}" + (
        f":{env['LIBRARY_PATH']}" if env.get("LIBRARY_PATH") else ""
    )
    env["LD_LIBRARY_PATH"] = f"{driver}:{cuda_target / 'lib'}" + (
        f":{env['LD_LIBRARY_PATH']}" if env.get("LD_LIBRARY_PATH") else ""
    )

    libbase = build / "identity_cuda"
    run_checked([futhark, "cuda", "--library", PROGRAM, "-o", libbase], env=env)

    binary = build / "transfer_probe"
    run_checked(
        [
            "cc",
            "-O2",
            "-std=c99",
            "-Wall",
            "-Wextra",
            "-I",
            build,
            "-I",
            cuda_target / "include",
            HARNESS,
            f"{libbase}.c",
            "-o",
            binary,
            "-L",
            driver,
            "-L",
            cuda_target / "lib",
            "-lcuda",
            "-lcudart",
            "-lnvrtc",
            "-lm",
            "-pthread",
            "-ldl",
        ],
        env=env,
    )

    raw_path = out / "transfer_raw.csv"
    rows: list[dict[str, int]] = []
    with raw_path.open("w", newline="", encoding="utf-8") as raw:
        writer = None
        for n in sizes:
            p = run_checked([binary, str(n), str(args.repeats)], env=env, capture=True)
            reader = csv.DictReader(p.stdout.splitlines())
            for record in reader:
                parsed = {k: int(v) for k, v in record.items()}
                rows.append(parsed)
                if writer is None:
                    writer = csv.DictWriter(raw, fieldnames=list(parsed))
                    writer.writeheader()
                writer.writerow(parsed)

    summary_rows = []
    for n in sizes:
        subset = [row for row in rows if row["elements"] == n]
        if len(subset) != args.repeats:
            raise SystemExit(f"expected {args.repeats} rows for {n}, got {len(subset)}")
        h2d = [row["h2d_import_ns"] for row in subset]
        kernel = [row["kernel_ns"] for row in subset]
        d2h = [row["d2h_export_ns"] for row in subset]
        h2d_bytes = subset[0]["h2d_import_bytes"]
        d2h_bytes = subset[0]["d2h_export_bytes"]
        h2d_med = median(h2d)
        kernel_med = median(kernel)
        d2h_med = median(d2h)
        summary_rows.append(
            {
                "elements": n,
                "h2d_import_bytes": h2d_bytes,
                "d2h_export_bytes": d2h_bytes,
                "h2d_import_median_us": h2d_med / 1000.0,
                "kernel_median_us": kernel_med / 1000.0,
                "d2h_export_median_us": d2h_med / 1000.0,
                "phase_sum_median_us": (h2d_med + kernel_med + d2h_med) / 1000.0,
                "h2d_import_effective_gb_s": h2d_bytes / h2d_med,
                "d2h_export_effective_gb_s": d2h_bytes / d2h_med,
            }
        )

    payload = {
        "schema": 1,
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "futhark": run_checked([futhark, "--version"], capture=True).stdout.strip(),
        "program": str(PROGRAM.relative_to(ROOT)),
        "entry_point": "validate_samples",
        "repeats": args.repeats,
        "measurement_semantics": {
            "h2d_import": "two futhark_new_i32_1d calls followed by futhark_context_sync; includes Futhark device allocation plus host-to-device import",
            "kernel": "futhark_entry_validate_samples followed by futhark_context_sync",
            "d2h_export": "futhark_values_bool_1d followed by futhark_context_sync",
            "context_creation": "excluded",
            "warmup": "one 256-element (or smaller) untimed call before evidence",
        },
        "rows": summary_rows,
    }
    (out / "transfer_summary.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print("elements,h2d_import_us,kernel_us,d2h_export_us,phase_sum_us,h2d_GB_s,d2h_GB_s")
    for row in summary_rows:
        print(
            f"{row['elements']},"
            f"{row['h2d_import_median_us']:.3f},"
            f"{row['kernel_median_us']:.3f},"
            f"{row['d2h_export_median_us']:.3f},"
            f"{row['phase_sum_median_us']:.3f},"
            f"{row['h2d_import_effective_gb_s']:.3f},"
            f"{row['d2h_export_effective_gb_s']:.3f}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
