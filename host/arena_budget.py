#!/usr/bin/env python3
"""Arena budget from a hardware profile (#98, stage S1).

The hardware profile is a *parameter*, not hard-coded: capacity is derived, so a
different card is a config change, not a rewrite.
"""
from __future__ import annotations

import json
import pathlib
import sys


def load_profile(path: str | None = None) -> dict:
    p = (
        pathlib.Path(path)
        if path
        else pathlib.Path(__file__).resolve().parent.parent / "hardware" / "profile.json"
    )
    return json.loads(p.read_text(encoding="utf-8"))


def budget(profile: dict) -> dict:
    """Derive the usable VRAM and the node capacity from a profile."""
    usable = int(profile["vram_total_bytes"]) - int(profile["reserved_bytes"])
    node = int(profile["node_bytes"])
    if node <= 0:
        raise ValueError("node_bytes must be positive")
    if usable <= 0:
        raise ValueError("reserved_bytes leaves no usable VRAM")
    return {
        "usable_bytes": usable,
        "node_bytes": node,
        "node_capacity": usable // node,
    }


def main() -> int:
    prof = load_profile()
    b = budget(prof)
    print(f"profile  = {prof['name']}")
    print(f"usable   = {b['usable_bytes']} B ({b['usable_bytes'] / 2**30:.2f} GiB)")
    print(f"node     = {b['node_bytes']} B")
    print(f"capacity = {b['node_capacity']} nodes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
