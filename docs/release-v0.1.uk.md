# Release v0.1 — шлях і evidence (#36)

## Що це

`sens-futhark` — **substrate** (witness / GPU acceleration), не друга реалізація мови.
Канонічна мова — pinned `juv4uk/sens` (`release/sens-source.pin`).

## Один шлях: мова (без GPU)

```bash
bash tools/verify-sens-source-pin.sh
# vendor/sens на pinned SHA (див. docs/sens-cli-entrypoint.uk.md)
bash tools/sens-cli.sh release/smoke/hello.lisp
# або
make sens-cli ARGS='release/smoke/hello.lisp'
make sens-cli-parity
```

## Один шлях: witness substrate

```bash
make bootstrap          # tools/install-futhark.sh → .tools/bin/futhark
make check-identity
make test-identity-cpu
make test-identity-cuda # потребує host CUDA 12.6 + runner labels
```

Команди не покладаються на неявний системний `futhark` у `$PATH` — використовуйте `FUTHARK=.tools/bin/futhark` або `make bootstrap`.

## Evidence manifest (заповнити після green run)

```text
repo_sha=
sens_pin=a4a83f2a879797bd431bd9896a52b707d7df7d53
futhark_version=0.27.1
cuda_toolkit=12.6
device=GTX 1050 Ti
cpu_witness=
cuda_witness=
run_url=
date=
```

## Статуси (чесні межі)

| статус | предмет |
|--------|----------|
| **CONFIRMED** | pin + entrypoint path; CPU identity witness (коли CI green) |
| **CONFIRMED\*** | CUDA identity на named self-hosted runner (коли green) |
| **BLOCKED** | OpenCL на поточному WSL host (`clGetPlatformIDs` −1001) |
| **UNRESOLVED** | canonical upstream fixture import (#31 / sens#3560) |

\* GPU — host-provided; Guix покриває CPU/import, не vendor CUDA.

## Non-claim

Finite Futhark kernel ≠ повна мова SENS. OpenCL parity без evidence не заявляється.
