# SENS → Futhark compiler backend

Status: **P1 implementation lane — contract/scaffold**

## Authority boundary

The canonical SENS compiler owns semantic derivation:

```text
juv4uk/sens
  exact-domain source
  → SENS-owned compiler lowering role
  → canonical backend-neutral request
```

This repository owns only target lowering:

```text
backend-neutral request
  → Futhark program
  → CUDA execution
```

The Futhark backend must never infer SENS meaning from:
- raw D3/D4 coordinates;
- packed width alone;
- Sid8/Sens8;
- English/Ukrainian surface names.

Compiler-role names in this document are API tags, not SENS language identities.

## Versioned backend envelope

Initial contract identifier:

```text
sens-futhark/compiler-backend/v1
```

Required provenance:

```text
source_repository
source_commit
contract
role_authority_digest
program_digest
backend
target
```

Each operation carries an already-verified backend-neutral role plus its exact-domain operands/arguments.

The backend is fail-closed when:
- contract/version is unknown;
- source commit does not match the pinned authority;
- role-authority digest is stale;
- an operation is not admitted by the backend capability set;
- required target support is missing.

## Compilation path

The first vertical slice is deliberately narrow:

```text
SENS source
  ↓
SENS-owned role derivation (#3824)
  ↓
compiler-backend/v1 request
  ↓
Futhark lowering
  ↓
futhark CUDA
  ↓
canonical observable / witness
```

The first executable GPU slice should consume operations that are already proven as data-parallel mechanisms. Host-control/compiler-form roles remain explicit non-GPU cases until there is an admitted device mechanism.

## Relationship to existing SENS-Futhark layers

- `docs/ir-contract.md`: exact-width transport; remains unchanged.
- `futhark/selector_law.fut`: existing mechanical structural projection; refreshed from upstream authority.
- `host/arena.py`: host reference for SoA layout and structural operations.
- `futhark/work_queue.fut`: bounded dispatch primitive for TDR-safe execution.
- `bench/`: performance evidence; no performance claim before measurements.

The compiler backend should feed these existing execution pieces instead of replacing them.

## Upstream coordination

Dependencies:

- `juv4uk/sens#3824`: final SENS-owned nine-role compiler closure;
- `juv4uk/sens#3801`: GPU admission;
- `juv4uk/sens#3802`: compact binary execution packet;
- `juv4uk/sens#3760`: fixed-point C0→C1→C2 evidence;
- `juv4uk/cml#606`: separate native CML IR admission path.

The backend must remain independent of CML-specific mechanism names.

## Falsification

This design is rejected if a Futhark lowering implementation needs to recover semantic meaning from an exact-domain coordinate, surface spelling, or legacy 8-bit identity. In that case the boundary has been violated and the implementation must stop rather than adding a compatibility shim.

## First proof target

For one admitted batch:

```text
compile(request)
  → Futhark source
  → CUDA result
```

must agree with a reference execution over the same backend-neutral request and preserve the request provenance byte-for-byte in the evidence envelope.

No claim of “full SENS compiler on GPU” is made by this first slice.
