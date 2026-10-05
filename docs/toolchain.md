# Futhark GPU toolchain

Issue: #1

## Pin

The first experiment pins **Futhark 0.27.1**. It is the latest stable release observed when this bootstrap was created (2026-10-05).

The compiler is installed repo-locally under `.tools/`; no system-wide Futhark install is required.

## Bootstrap

```bash
./tools/install-futhark.sh
./tools/probe-gpu.sh
./tools/smoke-opencl.sh
```

## Backend order

1. **OpenCL first** — establish the first GPU execution path without making CUDA-toolkit compatibility part of the semantic experiment.
2. **CUDA later** — issue #6 owns OpenCL/CUDA cross-backend parity. On the GTX 1050 Ti/Pascal machine, keep the CUDA path compatible with CUDA 12.x rather than making CUDA 13 a requirement.

## Scope boundary

This milestone is infrastructure only. `src/smoke.fut` must not encode D1-D8 rules, packed IR rules, or other SENS semantics. Those belong to #2/#4.

## Evidence to record before closing #1

Paste into #1:

- `futhark --version`;
- `nvidia-smi -L`;
- `clinfo -l` (or the concrete OpenCL-loader/ICD blocker);
- output of `./tools/smoke-opencl.sh`;
- exact blocker if OpenCL cannot see the GPU.

Do not claim GPU success from compilation alone: the generated executable must actually run.
