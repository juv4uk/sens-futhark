# Canonical packed SENS IR

Status: **L1 mechanical transport contract**.

This document describes only how an already-qualified SENS exact-width word stream is carried into the Futhark substrate. Semantic meaning remains upstream in `juv4uk/sens`.

## Authority

Upstream authority:

```text
SENS Contract 11.6
SENS commit a4a83f2a879797bd431bd9896a52b707d7df7d53
crates/sens/src/source_packing.rs
crates/sens/src/packed_bits.rs
```

The upstream implementation is the semantic/transport authority. This document narrows the backend boundary; it does not reimplement SENS semantics.

## L1 object

The canonical dense payload consists of:

```text
PackedPayload
  bytes[]       physical byte container
  bit_len       exact number of semantic payload bits

DecodeSchedule
  widths[]      caller-owned exact word widths
```

`bytes` alone is not an identity. `bit_len` is required. Word boundaries are not embedded in the dense payload and must come from the grammar/context that already owns them.

## Packing law

Already-tokenized exact-width source words are appended in program order, MSB-first, with **no padding between words**.

```text
word A | word B | word C | ...
```

A word may cross a physical byte boundary. The final byte may contain unused low bits; those bits are physical slack only and must be zero.

Packing never chooses semantic width. A 3-bit word remains a 3-bit word even if the backend stores the payload inside an 8-bit byte or a wider scalar.

## Unpacking law

Decoding requires an explicit caller-owned width schedule:

```text
sum(widths) == bit_len
1 <= width <= 8
```

Each word is read at its exact width from the dense bitstream. The decoder fails closed when the width schedule is invalid or does not consume the exact payload length.

Different schedules can legally describe the same raw payload. Therefore the packed payload does not silently recover grammar boundaries.

Example:

```text
0 00   -> bits 000
000    -> bits 000
```

The payload bytes are equal, but the source word sequences are different because their width schedules are different.

## Futhark representation

Futhark may use machine types such as `i32` or byte arrays as **physical carriers**. Those types are not SENS semantic domains.

Recommended mechanical input:

```text
packed_bytes : []u8 / physical byte array
bit_len      : i32 / physical metadata
widths       : []i32 / physical decode schedule
```

The host integration must preserve the exact source `(domain,bits)` identity before packing and reconstruct the exact words after unpacking.

## Framing boundary

Container framing, end-of-stream markers and width metadata are separate protocol concerns. They are not hidden inside the dense semantic payload.

Therefore this repository must not add a magic tag such as `SENS8`, `Function8`, a universal byte opcode, or a target-specific discriminator to the dense payload.

## Malformed input

Fail closed on:

- non-bit payload material;
- an empty/invalid width schedule when words are expected;
- width outside `1..8`;
- `sum(widths) != bit_len`;
- missing payload bytes;
- non-zero unused bits in the final physical byte;
- attempted domain collapse caused by padding or numeric reinterpretation.

## Reference vectors

Machine-readable vectors live in `tests/packed-ir-vectors.json`. They are mechanical transport witnesses derived from the upstream SENS packing implementation. They do not allocate semantic roles.

The first vector is the upstream canonical example:

```text
source words: 10 001 01
payload bits: 1000101
bit_len:      7
physical byte: 10001010
```

## Acceptance

An implementation passes this contract only when:

```text
unpack(pack(words), widths) == words
```

and the round-trip preserves the exact width schedule and exact `(domain,bits)` identities carried by the words.

Negative tests must prove that alternate padding, width loss and mismatched schedules do not pass.
