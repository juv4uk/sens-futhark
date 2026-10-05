# Futhark GPU toolchain

Issue: #1

## Pin

The first experiment pins **Futhark 0.27.1**. The compiler is installed repo-locally under `.tools/`; no system-wide Futhark install is required.

## Local GPU runner

Repository-scoped runner:

- name: `wsm-gpu-sens-futhark`;
- labels: `self-hosted, Linux, X64, gpu, gtx-1050-ti, cuda-12.6, sens-futhark`;
- GPU: NVIDIA GeForce GTX 1050 Ti;
- CUDA toolkit: 12.6;
- WSL2 GPU device: `/dev/dxg`.

## Bootstrap

```bash
make bootstrap
make probe
make smoke-cuda
```

`make smoke-opencl` is retained as a diagnostic path.

## Current backend evidence

### CUDA — working

The self-hosted GitHub Actions run compiled and executed `src/smoke.fut` with Futhark's CUDA backend on the GTX 1050 Ti.

Observed output:

```text
CUDA_ROOT=/usr/local/cuda-12.6
CUDA_TARGET=/usr/local/cuda-12.6/targets/x86_64-linux
== compile CUDA backend ==
== execute on CUDA device ==
[2i32, 3i32, 4i32, 5i32]
PASS: Futhark CUDA smoke test
```

The CUDA helper explicitly exposes:

- headers: `$CUDA_ROOT/targets/x86_64-linux/include`;
- toolkit libraries: `$CUDA_ROOT/targets/x86_64-linux/lib`;
- WSL driver library: `/usr/lib/wsl/lib`.

### OpenCL — loader present, platform absent

OpenCL headers and loader are installed, and the Futhark OpenCL executable compiles. Runtime enumeration currently fails under this WSL2/NVIDIA environment:

```text
clGetPlatformIDs(0, NULL, &num_platforms)
failed with error code -1001
```

`clinfo -l` reports no OpenCL platform. Therefore OpenCL is **not** counted as a GPU execution success on this host.

## Backend policy

1. Use **CUDA 12.6** as the current strict GPU execution witness on this GTX 1050 Ti.
2. Keep OpenCL as a diagnostic/conformance target and revisit it only when the host exposes an OpenCL platform.
3. Issue #6 owns later cross-backend parity work; it must not claim OpenCL parity on this machine while platform enumeration is unavailable.

## Scope boundary

This milestone is infrastructure only. `src/smoke.fut` must not encode SENS domain semantics. Canonical identity/IR rules remain owned by the SENS contract lane and the already-merged boundary/witness work.

## CI note

GitHub-hosted `ubuntu-latest` jobs are currently blocked by account billing/spending state before execution. The syntax check therefore uses the repository-scoped self-hosted runner.
