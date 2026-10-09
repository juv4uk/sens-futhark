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
make test-identity-cuda   # лише на підтвердженій CUDA-машині
```

`make test-identity-cpu` існує, але це **reference-only** — локальний семантичний референс, а не шлях релізу й не CI-лейн (див. політику нижче).

### CI: GitHub-hosted execution versus CUDA (#79)

Чинні `futhark.yml` та `compiler-slice.yml` запускають структурні
перевірки на `ubuntu-24.04` — **це не GPU-бенчмарки**. CUDA-гілки
допускаються лише за окремою умовою, але стандартний Ubuntu runner не
гарантує відеокарту. Якщо CUDA job пропущено, апаратна перевірка має
статус **UNVERIFIED** навіть тоді, коли workflow показує загальний
`success` за рахунок структурних jobs.

Перевірка маршрутизації —
`.github/workflows/hosted-runner-routing-policy.yml`.
Ніякої маршрутизації на локальні `self-hosted` ранери.
Планований окремий GPU fail-closed gate описано в PR #124; доки він не
ратифікований і не злитий, **не використовувати загальну зелену позначку
`futhark.yml` як доказ CUDA чи як достатню умову випуску**.

Попередні запуски GTX 1050 Ti / CUDA 12.6 є історичними свідченнями
конкретного локального хоста, а не живим GitHub-hosted GPU evidence.

## Evidence manifest

```bash
make release-evidence
```

Manifest заповнюється **з артефактів живого зеленого прогону** (#81), а не руками: скрипт бере `run_url` останнього success-прогону `GPU-only CUDA witnesses` на цьому SHA, читає `evidence/futhark/cuda.env` і ставить `cuda_witness` **лише якщо** `backend=cuda`. Деталі — `docs/release-evidence.uk.md`.

Обов'язкові поля: `repo_sha`, `sens_pin`, `futhark_version`, `cuda_witness`, `run_url`. Порожнє (або `unknown`) ⇒ **fail-closed**, `exit 2` — і **не** різати tag (#34).

## Статуси

| статус | предмет |
|--------|----------|
| **CONFIRMED** | pin + entrypoint; старі локальні CUDA-свідчення збережені як історичні |
| **REFERENCE** | CPU witness — внутрішній семантичний референс, не delivery-доказ (GPU-only #79) |
| **BLOCKED** | OpenCL WSL (−1001) |
| **UNRESOLVED** | upstream fixture import (#31 / sens#3560) |

## Non-claim

Finite Futhark kernel ≠ повна мова SENS.
