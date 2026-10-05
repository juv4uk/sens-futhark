# SENS integration boundary

Status: **backend integration contract**.

`sens-futhark` is downstream of `juv4uk/sens`. It consumes the SENS execution-conformance envelope; it does not define or duplicate SENS semantics.

## Authority chain

```text
juv4uk/sens
  Contract 11.6
  exact (domain,bits)
  execution-conformance/v1
        |
        v
sens-futhark
  Futhark mechanism
  CPU/GPU witness
```

The pinned upstream commit is recorded in `integration/sens-execution-conformance.lock`.

Current upstream cut at this integration point:

```text
D1-D7 = current
D8   = research / fail-closed
```

## What is imported

Only these upstream artifacts are part of the integration boundary:

```text
benchmarks/execution-ladder-conformance/README.md
benchmarks/execution-ladder-conformance/schema.json
benchmarks/execution-ladder-conformance/artifacts/bounded-d1-d3.summary.json
```

No SENS domain/function table is copied into this repository.

The bounded D1-D3 artifact is evidence only; its finite grammar is not a claim of exhaustive D1-D7 program coverage.

## Version discipline

Before a conformance run, the integration must verify:

1. the upstream checkout is exactly `SENS_COMMIT`;
2. every locked artifact has the expected Git blob SHA;
3. the evidence rows use `sens-execution-conformance/v1` and Contract `11.6`;
4. fresh evidence declares `legacy_identity_used=false`;
5. a contract/fixture mismatch fails closed.

Use:

```sh
python3 tools/verify-sens-integration.py --repo /path/to/sens --root /path/to/sens
```

The command checks the repository commit plus the exact locked artifact contents. Authentication for obtaining the upstream private repository is an environment concern; no semantic fallback exists when it cannot be obtained.

## Execution boundary

`sens-futhark` may transform the upstream evidence into backend-specific representations, but the parity authority remains the upstream canonical observable and `oracle_digest`.

```text
L0 ORACLE observable_digest
        ==
oracle_digest
        ==
downstream observable_digest
```

Backend availability is never a semantic decision. A missing mechanism is `BLOCKED-MECHANISM`; D8 remains research-only.

## Anti-drift rule

Do not update a local domain table when SENS changes. Refresh the upstream pin and rerun the verifier. Any semantic migration belongs in `juv4uk/sens` first.

## Next integration step

The next implementation lane should export one real SENS conformance JSONL case, feed it through the Futhark witness, and compare canonical observables with the existing fail-closed parity runner. The backend must report the exact case identity on divergence.
