# Canonical SENS boundary

Status: **implementation contract / backend guardrail**.

This repository must not become a second SENS language implementation.

## Authority

Semantic authority stays in [`juv4uk/sens`](https://github.com/juv4uk/sens) and its ratified contracts. `sens-futhark` consumes the result of the mechanical source projection.

The canonical identity entering this backend is:

```text
(domain, exact bits)
```

The identity is not:

- a machine byte,
- an integer without its domain,
- a function name,
- a historical `Sens8`/`Function8` value,
- or a GPU-specific opcode.

## Exact width

The source word keeps its width as domain context.

```text
D1  1
D2  01
D3  001
D4  0001
```

Equal packed payloads do not collapse across domains. In particular, `D1:1` and `D3:001` are distinct identities.

A backend may physically store both in the same scalar machine type. That is a representation decision only.

## Admitted domains

For the current backend boundary:

```text
D1  current
D2  current
D3  current
D4  current
D5  current
D6  current
D7  current
D8  research / fail-closed
```

The backend must never infer semantic admission merely from a domain number or from available machine capacity.

## Futhark rule

Futhark code may:

- validate the shape of an already-qualified identity;
- move and transform data for parallel execution;
- implement mechanisms whose semantics have already been defined upstream;
- participate in CPU/GPU parity witnesses.

Futhark code must not:

- assign semantic names to bit patterns;
- reconstruct semantics from physical width;
- introduce a parallel legacy function table;
- treat `u8`, `u16`, `u32`, etc. as SENS semantic domains.

The first module therefore validates only the mechanical identity shape. It intentionally does not implement SENS primitive semantics.

## Next witness

The next implementation should add a shared golden corpus for exact identities and run the same corpus through CPU and GPU execution paths. Any mismatch must identify the exact `(domain,bits)` pair that diverged.
