# Identity benchmark harness

Issue: #5.

This directory measures the **already-merged** exact-identity witness.  It does not
define or extend SENS semantics.

## Workload

The harness benchmarks `futhark/identity_witness.fut:validate_samples` with
D7-valid inputs:

- domain array: every element is `7`;
- bit array: values are generated in the inclusive range `0..127`;
- both arrays use Futhark's binary data format.

Default batch sizes are:

`256, 1K, 4K, 16K, 64K, 256K, 1M, 4M`.

The exact same generated dataset file is consumed by the sequential C backend
and the CUDA backend.

## Measurements

`bench/run.py` records separately:

- C and CUDA compile wall time;
- repeated cold process end-to-end latency on the smallest dataset;
- steady-state `futhark bench` raw JSON for C and CUDA;
- CUDA profiling data for kernel and memory-copy cost centres;
- machine, compiler, Git commit, GPU and CUDA metadata.

Raw data is authoritative.  Summaries must be derived from it; a slower GPU is
a valid outcome.

## Run

After a Futhark toolchain is available:

```bash
python3 bench/run.py --futhark /path/to/futhark
```

For a quick validation:

```bash
python3 bench/run.py \
  --futhark /path/to/futhark \
  --sizes 256,4096,65536 \
  --runs 3 \
  --cold-runs 2 \
  --out /tmp/sens-futhark-bench
```

Generated datasets and results are intentionally not committed.  CI artifacts
or explicitly selected evidence snapshots may be preserved separately.

## Interpretation boundary

The benchmark compares execution substrates.  It must not be used as evidence
that CUDA, C, Futhark, or any other backend owns SENS semantic authority.
