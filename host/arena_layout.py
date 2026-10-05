#!/usr/bin/env python3
"""Node layout arithmetic for the SoA arena (#98, stage S1).

The device layout is *derived* from the field list, not hand-written: offsets and
alignment padding are computed, so the 24 B budget can be checked, not asserted.
"""
from __future__ import annotations

# (name, type, size_bytes, align_bytes) — order is the SoA field order.
NODE_FIELDS = (
    ("tag", "u8", 1, 1),
    ("domain", "u32", 4, 4),
    ("left", "u32", 4, 4),
    ("right", "u32", 4, 4),
    ("value", "i64", 8, 8),
)


def _align_up(n: int, a: int) -> int:
    return (n + a - 1) // a * a


def layout(fields=NODE_FIELDS) -> dict:
    """Return field offsets plus the packed (SoA) and aligned (struct) sizes.

    packed_bytes — sum of field sizes, what separate SoA arrays actually cost.
    struct_bytes — packed_bytes plus alignment padding, the AoS cost.
    """
    offset = 0
    offsets = {}
    for name, _type, size, align in fields:
        offset = _align_up(offset, align)
        offsets[name] = offset
        offset += size
    packed = sum(size for _n, _t, size, _a in fields)
    max_align = max(align for _n, _t, _s, align in fields)
    struct = _align_up(offset, max_align)
    return {"offsets": offsets, "packed_bytes": packed, "struct_bytes": struct}
