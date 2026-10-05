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
make test-identity-cuda   # єдиний CI-шлях: self-hosted CUDA
```

`make test-identity-cpu` існує, але це **reference-only** — локальний семантичний референс, а не шлях релізу й не CI-лейн (див. політику нижче).

### CI (GPU-only, #79)

Єдиний воркфлоу — `.github/workflows/futhark.yml` (`GPU-only CUDA witnesses`).

| job | runs-on | status |
|-----|---------|--------|
| `CUDA-only witness` (`futhark.yml`) | `[self-hosted, Linux, X64, gpu, cuda-12.6, sens-futhark]` | **green on main** (run 37377715294) |
| OpenCL | — | **BLOCKED** −1001 |

CPU-лейни в CI **немає**: `cpu-witness.yml` видалено, а спроба #75 винести CPU на `ubuntu-24.04` впала **до першого кроку** і була відкочена. CUDA недоступна ⇒ job падає **fail-closed**, без фолбеку на `--backend=c`.

## Evidence manifest

```bash
make release-evidence
```

Manifest заповнюється **з артефактів живого зеленого прогону** (#81), а не руками: скрипт бере `run_url` останнього success-прогону `GPU-only CUDA witnesses` на цьому SHA, читає `evidence/futhark/cuda.env` і ставить `cuda_witness` **лише якщо** `backend=cuda`. Деталі — `docs/release-evidence.uk.md`.

Обов'язкові поля: `repo_sha`, `sens_pin`, `futhark_version`, `cuda_witness`, `run_url`. Порожнє (або `unknown`) ⇒ **fail-closed**, `exit 2` — і **не** різати tag (#34).

## Статуси

| статус | предмет |
|--------|----------|
| **CONFIRMED** | pin + entrypoint; CUDA witness зелений на main (self-hosted, GTX 1050 Ti) |
| **REFERENCE** | CPU witness — внутрішній семантичний референс, не delivery-доказ (GPU-only #79) |
| **BLOCKED** | OpenCL WSL (−1001) |
| **UNRESOLVED** | upstream fixture import (#31 / sens#3560) |

## Non-claim

Finite Futhark kernel ≠ повна мова SENS.
