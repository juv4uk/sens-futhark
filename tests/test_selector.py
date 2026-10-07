#!/usr/bin/env python3
"""Tests for the selector-law table (stage S2, #96).

Runnable with plain python:  python3 tests/test_selector.py
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from host.selector import CLASSES, RESIDENCY, SelectorTable  # noqa: E402

MAP = pathlib.Path(__file__).resolve().parent.parent / "data" / "d7-full-map.json"


def test_table_shape():
    t = SelectorTable.from_map(MAP)
    assert t.capacity == 128, t.capacity
    assert len(t.rows) == 128
    assert all(r is not None for r in t.rows), "table must be complete"
    print(f"ok: table {t.name} is dense and complete ({t.capacity} rows)")


def test_top2_determines_class():
    """The map's own occupancy_rule: class = top 2 bits."""
    t = SelectorTable.from_map(MAP)
    seen: dict[str, str] = {}
    for code in range(t.capacity):
        top2 = format(code, "07b")[:2]
        cls = t.class_of(code)
        assert cls in CLASSES, cls
        if top2 in seen:
            assert seen[top2] == cls, f"top2 {top2} -> both {seen[top2]} and {cls}"
        else:
            seen[top2] = cls
    assert len(seen) == 4, seen
    print(f"ok: class is determined by the top 2 bits: {seen}")


def test_counts_match_status_counts():
    data = json.loads(MAP.read_text(encoding="utf-8"))
    t = SelectorTable.from_map(data)
    expected = data["status_counts"]["cells"]
    got = collections.Counter(t.residency_of(c) for c in range(t.capacity))
    assert got["assigned"] == expected["assigned"], (got, expected)
    assert got["reserved"] == expected["reserved"], (got, expected)
    assert sum(got.values()) == expected["total"]
    print(f"ok: residency counts match status_counts: {dict(got)}")


def test_unknown_code_fails_closed():
    t = SelectorTable.from_map(MAP)
    assert t.lookup(t.capacity) is None
    assert t.handler(-1) is None
    assert t.class_of(t.capacity + 5) is None
    print("ok: out-of-range codes fail closed (None)")


if __name__ == "__main__":
    test_table_shape()
    test_top2_determines_class()
    test_counts_match_status_counts()
    test_unknown_code_fails_closed()
    print("ALL OK")
