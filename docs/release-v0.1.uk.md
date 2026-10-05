# Release v0.1 — шлях і evidence (#36)

## Що це

`sens-futhark` — **substrate** (witness / GPU acceleration), не друга реалізація мови.
Канонічна мова — pinned `juv4uk/sens` (`release/sens-source.pin`).

**Tip:** `git rev-parse HEAD` / `make release-evidence`.

## Один шлях: мова (без GPU)

```bash
bash tools/verify-sens-source-pin.sh
# vendor/sens на pinned SHA (див. docs/sens-cli-entrypoint.uk.md)
bash tools/sens-cli.sh release/smoke/hello.lisp
make sens-cli ARGS='release/smoke/hello.lisp'
make sens-cli-parity
```

## Один шлях: witness substrate

```bash
make bootstrap
make check-identity
make test-identity-cpu
make test-identity-cuda   # self-hosted CUDA only
```

### CI

| job | runs-on | status |
|-----|---------|--------|
| CPU reference witness (`cpu-witness.yml`) | self-hosted `sens-futhark` | hosted route #75 failed before step 1; чекає #69 listener recovery |
| Futhark CUDA / GPU smoke | self-hosted `sens-futhark` | чекає #69 host recovery |
| OpenCL | — | **BLOCKED** −1001 |

## Evidence manifest

```bash
make release-evidence
```

Заповнюйте `cpu_witness` / `cuda_witness` / `run_url` **лише** після live green runs.
Порожні поля ⇒ **не** різати tag (#34).

Спроба #75 перенести CPU на `ubuntu-24.04` завершилась failure **до першого step** (#83), тому hosted route не рахується доказом і тимчасово відкочений. CPU run URL заноситься в evidence лише після live green.

## Статуси

| статус | предмет |
|--------|----------|
| **CONFIRMED** | pin + entrypoint; CPU witness семантично не потребує GPU |
| **PENDING** | live green CPU/CUDA після #69 listener recovery; run_url у manifest |
| **BLOCKED** | OpenCL WSL (−1001); CUDA self-hosted until #69 recovery |
| **UNRESOLVED** | upstream fixture import (#31 / sens#3560) |

## Non-claim

Finite Futhark kernel ≠ повна мова SENS.
