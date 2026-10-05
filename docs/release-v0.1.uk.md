# Release v0.1 — шлях і evidence (#36)

## Що це

`sens-futhark` — **substrate** (witness / GPU acceleration), не друга реалізація мови.
Канонічна мова — pinned `juv4uk/sens` (`release/sens-source.pin`).

**Tip (код шляху мови):** див. `git rev-parse HEAD` / `make release-evidence`.

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
make bootstrap
make check-identity
make test-identity-cpu
make test-identity-cuda
```

Команди не покладаються на неявний системний `futhark` у `$PATH`.

## Evidence manifest

```bash
make release-evidence
```

Виводить `repo_sha`, `sens_pin`, `futhark_version`, порожні `cpu_witness` / `cuda_witness` / `run_url`.
Заповнюйте їх **лише** після live green self-hosted runs. Порожні поля ⇒ **не** різати tag (#34).

## Статуси (чесні межі)

| статус | предмет |
|--------|----------|
| **CONFIRMED** | pin + entrypoint path на main |
| **PENDING** | CPU/CUDA identity — live green run URL |
| **BLOCKED** | OpenCL WSL (`clGetPlatformIDs` −1001) |
| **UNRESOLVED** | upstream fixture import (#31 / sens#3560) |

## Non-claim

Finite Futhark kernel ≠ повна мова SENS. OpenCL parity без evidence не заявляється.
