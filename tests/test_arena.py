#!/usr/bin/env python3
"""Tests for the SoA arena and the profile-driven budget (#98, stage S1).

Runnable with plain python (no pytest needed):  python3 tests/test_arena.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from host.arena import ATOM, PAIR, Arena, ArenaError  # noqa: E402
from host.arena_budget import budget, load_profile  # noqa: E402
from host.arena_layout import layout  # noqa: E402


class Naive:
    """Naive tree reference to check the arena against."""

    __slots__ = ("tag", "value", "left", "right")

    def __init__(self, tag, value=None, left=None, right=None):
        self.tag = tag
        self.value = value
        self.left = left
        self.right = right


def to_naive(a: Arena, i: int) -> Naive:
    if a.tag[i] == ATOM:
        return Naive(ATOM, value=a.atom_value(i))
    return Naive(PAIR, left=to_naive(a, a.car(i)), right=to_naive(a, a.cdr(i)))


def naive_equal(x: Naive, y: Naive) -> bool:
    if x.tag != y.tag:
        return False
    if x.tag == ATOM:
        return x.value == y.value
    return naive_equal(x.left, y.left) and naive_equal(x.right, y.right)


def test_ops_match_naive():
    a = Arena(64)
    nil = a.alloc_atom(0, domain=0)
    n3 = a.alloc_atom(3, domain=1)
    p3 = a.alloc_pair(n3, nil, domain=2)
    n2 = a.alloc_atom(2, domain=1)
    p2 = a.alloc_pair(n2, p3, domain=2)
    n1 = a.alloc_atom(1, domain=1)
    p1 = a.alloc_pair(n1, p2, domain=2)

    expected = Naive(
        PAIR,
        left=Naive(ATOM, value=1),
        right=Naive(
            PAIR,
            left=Naive(ATOM, value=2),
            right=Naive(PAIR, left=Naive(ATOM, value=3), right=Naive(ATOM, value=0)),
        ),
    )
    assert naive_equal(to_naive(a, p1), expected), "arena tree != naive tree"
    print("ok: ops match naive")


def test_errors_fail_closed():
    a = Arena(8)
    atom = a.alloc_atom(5, domain=1)
    for fn in (a.car, a.cdr):
        try:
            fn(atom)
            raise AssertionError("expected ArenaError")
        except ArenaError:
            pass
    try:
        a.atom_value(a.alloc_pair(atom, atom, 2))
        raise AssertionError("expected ArenaError")
    except ArenaError:
        pass
    print("ok: invalid ops fail closed")


def test_dispatch_is_table_lookup():
    a = Arena(8)
    a.register(7, 42)
    x = a.alloc_atom(1, domain=7)
    y = a.alloc_atom(1, domain=9)
    assert a.dispatch(x) == 42
    assert a.dispatch(y) is None, "unknown domain must be None, not a silent default"
    print("ok: dispatch is a table lookup, unknown -> None")


def test_compaction_frees():
    a = Arena(256)
    nil = a.alloc_atom(0, domain=0)
    root = nil
    for k in range(1, 11):
        root = a.alloc_pair(a.alloc_atom(k, domain=1), root, domain=2)
    # garbage, unreachable from root
    for k in range(50):
        a.alloc_pair(a.alloc_atom(k, domain=1), nil, domain=2)

    before_tree = to_naive(a, root)
    before = a.used_bytes()
    new_roots, live = a.compact([root])
    after = a.used_bytes()

    assert after < before, f"compaction did not free: {before} -> {after}"
    assert naive_equal(to_naive(a, new_roots[0]), before_tree), "structure lost in compaction"
    print(f"ok: compaction freed {before - after} B ({live} live nodes)")


def test_budget_from_profile():
    prof = load_profile()
    b = budget(prof)
    assert b["usable_bytes"] == 3 * 2**30, b
    assert b["node_capacity"] == 134_217_728, b
    print(f"ok: budget = {b['node_capacity']} nodes from {prof['name']}")


def test_layout_arithmetic():
    lay = layout()
    assert lay["offsets"] == {"tag": 0, "domain": 4, "left": 8, "right": 12, "value": 16}, lay
    assert lay["packed_bytes"] == 21, lay
    assert lay["struct_bytes"] == 24, lay
    print("ok: layout derived -> packed 21 B, struct 24 B")


def test_buffer_roundtrip():
    a = Arena(64)
    nil = a.alloc_atom(0, domain=0)
    root = a.alloc_pair(a.alloc_atom(7, domain=1), nil, domain=2)
    bufs = a.to_buffers()
    b = Arena.from_buffers(bufs)
    assert naive_equal(to_naive(b, root), to_naive(a, root)), "buffer roundtrip lost structure"
    # SoA buffers are tightly packed: total nbytes == capacity * packed_bytes
    total = sum(bufs[k].nbytes for k in ("tag", "domain", "left", "right", "value"))
    assert total == a.capacity * 21, (total, a.capacity * 21)
    print(f"ok: buffer roundtrip preserved the tree; packed {total} B")


def test_soa_packing_is_tighter():
    prof = load_profile()
    aos = budget(prof, "aos")
    soa = budget(prof, "soa")
    assert aos["node_bytes"] == 24 and soa["node_bytes"] == 21
    assert soa["node_capacity"] > aos["node_capacity"], (soa, aos)
    print(
        f"ok: soa {soa['node_capacity']} nodes > aos {aos['node_capacity']} nodes "
        f"({soa['node_capacity'] - aos['node_capacity']} more)"
    )


if __name__ == "__main__":
    test_ops_match_naive()
    test_errors_fail_closed()
    test_dispatch_is_table_lookup()
    test_compaction_frees()
    test_budget_from_profile()
    test_layout_arithmetic()
    test_buffer_roundtrip()
    test_soa_packing_is_tighter()
    print("ALL OK")
