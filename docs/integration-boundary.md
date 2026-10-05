# Межа інтеграції SENS → Futhark

`juv4uk/sens` володіє семантикою, admitted domains і canonical fixture
source. `sens-futhark` є optional execution substrate: він приймає вже
визначену exact identity, перевіряє provenance bundle і виконує CPU/Futhark
mechanism. Він не створює semantic law, name lookup або нову domain table.

## Bundle schema v1

Source directory містить `manifest.json` і `identity_vectors.csv`.

```json
{
  "schema": "sens-fixture-bundle/1",
  "source_repository": "juv4uk/sens",
  "source_commit": "40 lowercase hexadecimal characters",
  "contract_version": "upstream contract identifier",
  "payload": "identity_vectors.csv",
  "payload_sha256": "64 lowercase hexadecimal characters"
}
```

CSV має точний header `domain,width,bits,exact_text`. Importer звіряє digest
до копіювання й не приймає duplicate `(domain,bits)` identities. Він не
виводить допустимість доменів із machine width: це лишається upstream
authority.

## Failure is evidence

Unknown schema, чужий source repository, invalid commit/digest, altered CSV,
duplicate identity або malformed header зупиняють import до CPU чи backend
execution. Немає fallback на локальний CSV.

Upstream export ще має бути створений у межах
[sens#3560](https://github.com/juv4uk/sens/issues/3560). Отже
`fixtures/example/` є тільки synthetic protocol fixture, не canonical SENS
data і не доказом GPU parity.

`make witness-parity` приймає явний `BACKEND_WITNESS` та використовує
`host/parity.py` (#18). Він порівнює спостереження keyed by `(domain,bits)`;
відсутній backend output або parity runner — fail-closed failure.
