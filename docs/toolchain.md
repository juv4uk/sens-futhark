# Futhark GPU toolchain

Issues: #1, #41  
Shared host contract: `juv4uk/ecosystem#58`  
CML consumer: `juv4uk/cml#535`

## Pin

The first experiment pins **Futhark 0.27.1**. The compiler is installed repo-locally under `.tools/`; no system-wide Futhark install is required.

## GPU host profile

`tools/cuda-env.sh` is the reusable, backend-neutral host capability layer.

It can be sourced by a backend:

```bash
source tools/cuda-env.sh
cuda_env_require
```

or executed directly:

```bash
bash tools/cuda-env.sh env
bash tools/cuda-env.sh json
bash tools/cuda-env.sh run <command> [args...]
```

The helper normalizes and exports:

- `CUDA_HOME` / `CUDA_PATH`;
- `CUDA_ROOT` and `CUDA_TARGET`;
- `CUDA_INCLUDE`;
- `CUDA_TOOLKIT_LIB`;
- `CUDA_DRIVER_LIB`;
- `CPATH`, `LIBRARY_PATH`, and `LD_LIBRARY_PATH`.

The default toolkit root remains `/usr/local/cuda-12.6`, but callers may override it through `CUDA_HOME` or `CUDA_PATH`.

For driver discovery, WSL2's `/usr/lib/wsl/lib` is preferred when present. Native Linux falls back to the system `ldconfig` view. This keeps the contract tied to observed host capability rather than to WSL-specific semantics.

## Machine-readable capability

Run:

```bash
make probe-cuda-json
```

The JSON record reports:

- overall status;
- host kind (`wsl2` or `native-linux`);
- normalized toolkit/include/library paths;
- header, driver, and device visibility;
- device name;
- compute capability when exposed by `nvidia-smi`;
- driver version;
- `nvcc` version when present.

A CUDA execution path calls `cuda_env_require` and fails closed when `cuda.h`, the CUDA driver library, or a visible device is missing.

The ordinary `make probe` remains diagnostic and also prints the capability JSON; it does not turn a missing GPU into semantic success.

## GitHub-hosted runner policy (current)

GitHub Actions now targets **GitHub-hosted** machines exclusively. The policy
workflow validates `RUNNER_ENVIRONMENT=github-hosted` and the routing
checker permits only explicitly reviewed runner images. The old repository
`self-hosted` runner registration, its WSL service, GTX 1050 Ti and CML
single-device queue are **historical/local tooling**, not a valid CI target.

Standard `ubuntu-24.04` is a CPU host; a skipped CUDA job is
`UNVERIFIED`, not successful CUDA parity. A genuine GitHub-hosted GPU runner
needs separate provisioning and device evidence before any claim of a CUDA
benchmark. See `docs/gpu-scheduler-invariant.uk.md`.

## Bootstrap

```bash
make bootstrap
make probe
make smoke-cuda
```

`make smoke-opencl` is retained as a diagnostic path.

## Current backend evidence

### CUDA — historical local witness (not current hosted CI proof)

A historical self-hosted GitHub Actions run compiled and executed `src/smoke.fut` with Futhark's CUDA backend on the GTX 1050 Ti.

The host profile resolves the current WSL2 installation to:

```text
CUDA_ROOT=/usr/local/cuda-12.6
CUDA_TARGET=/usr/local/cuda-12.6/targets/x86_64-linux
CUDA_INCLUDE=/usr/local/cuda-12.6/targets/x86_64-linux/include
CUDA_TOOLKIT_LIB=/usr/local/cuda-12.6/targets/x86_64-linux/lib
CUDA_DRIVER_LIB=/usr/lib/wsl/lib
```

The Futhark smoke then executes:

```text
== compile CUDA backend ==
== execute on CUDA device ==
[2i32, 3i32, 4i32, 5i32]
PASS: Futhark CUDA smoke test
```

`test-identity-cuda`, packed-domain CUDA testing, and `smoke-cuda` all consume the same host profile rather than carrying separate CUDA path recipes.

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
4. The host profile proves capability only. It does not prove that a workload belongs on GPU or that GPU execution is faster.

## Scope boundary

This milestone is infrastructure only. `src/smoke.fut` must not encode SENS domain semantics. Canonical identity/IR rules remain owned by the SENS contract lane and the already-merged boundary/witness work.

The execution boundary is:

```text
CPU-hosted runner / compiler / coordination
             |
             v
      bounded GPU backend
             |
             v
        CUDA device
```

The GitHub runner itself still executes as a host process. Only explicitly admitted kernels or backend work execute on the GPU.

## CI note (current)

The GitHub-hosted route checker executes on `ubuntu-24.04`. Its success does
not attest to CUDA device availability. A hosted CUDA hardware witness must
be recorded separately; no local runner fallback is permitted.
