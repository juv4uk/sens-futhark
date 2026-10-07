#!/usr/bin/env python3
"""Selector-law table: exact-domain code -> dispatch row (stage S2, #96).

The law is a *table*, not code: a domain code indexes a dense row of
(class, residency, handler). This is what lets the same meaning run on a
different substrate — the meaning stays a table, the substrate stays a lookup.
"""
from __future__ import annotations

import json
from pathlib import Path

CLASSES = ("varga", "non-varga", "vowel", "sign/operator")
RESIDENCY = ("assigned", "reserved")


class SelectorError(Exception):
    """Raised when a law map cannot be turned into a complete table (fail-closed)."""


class SelectorTable:
    """A dense table indexed by the exact-domain code."""

    def __init__(self, capacity: int, rows: list, name: str = "selector"):
        self.capacity = int(capacity)
        self.rows = rows
        self.name = name

    @classmethod
    def from_map(cls, source) -> "SelectorTable":
        data = (
            json.loads(Path(source).read_text(encoding="utf-8"))
            if isinstance(source, (str, Path))
            else source
        )
        capacity = int(data["capacity"])
        rows = [None] * capacity
        for row in data["coordinates"]:
            code = int(row["hex"], 16)
            if not 0 <= code < capacity:
                raise SelectorError(f"coordinate {row['coordinate']} out of range")
            rows[code] = {
                "class": row["class"],
                "residency": row["residency"],
                "handler": f"{row['class']}:{row['residency']}",
                "name": row.get("name"),
            }
        missing = [i for i, r in enumerate(rows) if r is None]
        if missing:
            raise SelectorError(f"map leaves {len(missing)} codes unset (fail-closed)")
        return cls(capacity, rows, name=data.get("domain", "selector"))

    def lookup(self, code: int):
        if not 0 <= code < self.capacity:
            return None
        return self.rows[code]

    def handler(self, code: int):
        row = self.lookup(code)
        return None if row is None else row["handler"]

    def class_of(self, code: int):
        row = self.lookup(code)
        return None if row is None else row["class"]

    def residency_of(self, code: int):
        row = self.lookup(code)
        return None if row is None else row["residency"]
