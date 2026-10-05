# sens-futhark

Експериментальний GPU host/backend для SENS через Futhark.

## Межа влади

`sens-futhark` є **execution substrate**, а не семантичною владою. Мова,
domains і semantic laws належать [`juv4uk/sens`](https://github.com/juv4uk/sens).
Backend отримує вже визначену identity `(domain, exact bits)` і не може
відновлювати значення з machine width, текстового імені чи legacy
`Sens8`/`Function8` table.

За Contract 11.6 D1–D7 є current domains; D8 — research і тут fail-closed.
Однаковий payload у різних domains лишається різною identity.

## Докази та межі

CUDA witness на self-hosted GTX 1050 Ti з CUDA 12.6 уже зафіксовано як
execution evidence. OpenCL loader на WSL2 наявний, але OpenCL platform
**відсутня** (`clGetPlatformIDs … -1001`), тому OpenCL не заявляється
робочим backend-ом. CPU self-comparison або synthetic fixture не є GPU parity.

## Import і witness

Локальний CSV не є канонічним джерелом. `sens-futhark` приймає лише
versioned bundle від `juv4uk/sens` із source commit, contract version і
SHA-256 payload. До появи upstream export live import чесно заблокований;
`fixtures/example/` доводить тільки importer protocol.

```sh
make import-fixture SENS_FIXTURE_SOURCE=/шлях/до/sens-bundle
make witness-cpu
make witness-parity BACKEND_WITNESS=/шлях/до/backend-witness.txt
```

Відсутній fixture, runner або backend output є помилкою, не доказом
паритету. Деталі: [docs/integration-boundary.md](docs/integration-boundary.md).

## Guix

```sh
./guix/run dev -- python3 host/cpu_witness.py --self-test
./guix/run futhark -- make check-identity
```

Guix описує лише відтворюване CPU/import середовище. Futhark і CUDA на WSL є
optional host-provided capability; Guix profile не гарантує ні device, ні
semantic admission. Деталі: [guix/README.uk.md](guix/README.uk.md).

## Ліцензія

Власна юридично віддільна робота цього репозиторію поширюється під
[ВОЛЬНІСТЮ](LICENSE). Сторонні інструменти, зокрема Futhark, зберігають свої
власні умови та provenance.
