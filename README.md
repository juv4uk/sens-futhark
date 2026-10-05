# sens-futhark

Experimental GPU host/backend for SENS using Futhark.

## Boundary

`sens-futhark` is a **substrate**, not a semantic authority.

The semantic source of truth remains [`juv4uk/sens`](https://github.com/juv4uk/sens). The backend receives an already-qualified SENS identity:

```text
(domain, exact bits)
```

The domain fixes the semantic width. Physical storage may use a wider machine type for GPU efficiency, but physical width never creates or changes SENS meaning.

Current policy follows SENS Contract 11.6:

- D1-D7 are current semantic domains.
- D8 is research-only and must fail closed in this backend until separately ratified.
- Equal payloads in different domains remain different identities (`1`, `01`, `001`, ...).
- No legacy `Sens8` / `Function8` lookup is allowed in the canonical path.
- Futhark performs mechanism only; semantic laws remain owned by SENS.

## Initial slice

The first implementation lane establishes the exact-identity boundary and a tiny Futhark validator. CPU and GPU witnesses will later consume the same vectors and compare semantic observations, not backend-specific representations.

See [`docs/canonical-boundary.md`](docs/canonical-boundary.md) and issue [#9](https://github.com/juv4uk/sens-futhark/issues/9).

## Import і witness

Локальний CSV не є канонічним джерелом. `sens-futhark` приймає тільки
versioned bundle, який називає `juv4uk/sens`, source commit, версію контракту
й SHA-256 payload. До появи такого export в upstream import лишається чесно
заблокованим — synthetic bundle у `fixtures/example/` доводить тільки
механіку importer-а.

```sh
make import-fixture SENS_FIXTURE_SOURCE=/шлях/до/sens-bundle
make witness-cpu
make witness-parity BACKEND_WITNESS=/шлях/до/backend-witness.txt
```

`witness-parity` не запускає GPU і не створює backend output: він лише
порівнює явно наданий witness із CPU reference. Відсутній runner, fixture або
backend output є помилкою, а не доказом паритету.
