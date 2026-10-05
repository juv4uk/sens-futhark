#!/usr/bin/env python3
"""Summarise Futhark bench JSON without changing benchmark evidence."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


def load_datasets(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if len(payload) != 1:
        raise SystemExit(f"expected one benchmark entry in {path}, got {len(payload)}")
    return next(iter(payload.values()))["datasets"]


def percentile(values: list[int], p: float) -> int:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * p)))
    return ordered[index]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("directory", type=Path)
    args = ap.parse_args()

    root = args.directory
    cpu = load_datasets(root / "c.json")
    gpu = load_datasets(root / "cuda.json")

    rows = []
    first_cuda_win = None
    for name in sorted(cpu, key=lambda s: int(s.rsplit("-", 1)[-1])):
        if name not in gpu:
            raise SystemExit(f"dataset missing from CUDA results: {name}")
        n = int(name.rsplit("-", 1)[-1])
        c_runs = cpu[name]["runtimes"]
        g_runs = gpu[name]["runtimes"]
        c_med = float(statistics.median(c_runs))
        g_med = float(statistics.median(g_runs))
        speedup = c_med / g_med
        if first_cuda_win is None and speedup > 1.0:
            first_cuda_win = n
        rows.append(
            {
                "elements": n,
                "c_median_us": c_med,
                "c_p10_us": percentile(c_runs, 0.10),
                "c_p90_us": percentile(c_runs, 0.90),
                "c_throughput_melem_s": n / c_med,
                "cuda_median_us": g_med,
                "cuda_p10_us": percentile(g_runs, 0.10),
                "cuda_p90_us": percentile(g_runs, 0.90),
                "cuda_throughput_melem_s": n / g_med,
                "cuda_over_c_speedup": speedup,
                "cuda_kernel_profile_us": (
                    gpu[name].get("profiling", {}).get("events", [{}])[0].get("duration")
                    if gpu[name].get("profiling", {}).get("events")
                    else None
                ),
            }
        )

    first_sustained_cuda_win = None
    for i, row in enumerate(rows):
        if row["cuda_over_c_speedup"] > 1.0 and all(
            later["cuda_over_c_speedup"] > 1.0 for later in rows[i:]
        ):
            first_sustained_cuda_win = row["elements"]
            break

    summary = {
        "schema": 2,
        "runtime_unit": "microseconds",
        "first_measured_median_cuda_win_elements": first_cuda_win,
        "first_sustained_cuda_win_elements": first_sustained_cuda_win,
        "rows": rows,
    }
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print("elements,c_median_us,cuda_median_us,cuda_over_c_speedup,cuda_kernel_profile_us")
    for row in rows:
        print(
            f"{row['elements']},{row['c_median_us']:.3f},"
            f"{row['cuda_median_us']:.3f},{row['cuda_over_c_speedup']:.4f},"
            f"{row['cuda_kernel_profile_us']}"
        )
    print(f"first_measured_median_cuda_win_elements={first_cuda_win}")
    print(f"first_sustained_cuda_win_elements={first_sustained_cuda_win}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
