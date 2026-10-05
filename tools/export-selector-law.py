#!/usr/bin/env python3
"""Project the pinned SENS selector law into a device lookup table.

The upstream Rust law remains authoritative. This script only parses its
explicit width bound, D3 roots, and suffix step mapping, then enumerates the
admitted D3-D5 identities. It fails closed if the upstream law shape changes.
"""
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
pin = root / "release" / "sens-source.pin"
source = root / "vendor" / "sens" / "crates" / "sens" / "src" / "eval" / "selector_law.rs"

if not pin.exists() or not source.exists():
    raise SystemExit("fail-closed: run 'make sens-fetch' before exporting selector law")

text = source.read_text(encoding="utf-8")
pin_text = pin.read_text(encoding="utf-8")
commit = re.search(r"^SENS_COMMIT=([0-9a-f]{40})$", pin_text, re.M)
if not commit:
    raise SystemExit("fail-closed: invalid SENS_COMMIT pin")
commit = commit.group(1)

width = re.search(r"if !\(3\.\.=([0-9]+)\)\.contains\(&width\)", text)
if not width or int(width.group(1)) != 5:
    raise SystemExit("fail-closed: unsupported selector width bound")
if "0b100 => Step::Car" not in text or "0b011 => Step::Cdr" not in text:
    raise SystemExit("fail-closed: expected ratified D3 selector roots missing")
if "((payload >> shift) & 1) == 0" not in text:
    raise SystemExit("fail-closed: expected suffix CAR/CDR projection missing")

rows = []
for w in range(3, 6):
    for raw in range(1 << w):
        prefix = raw >> (w - 3)
        if prefix not in (0b100, 0b011):
            continue
        steps = ("CAR" if prefix == 0b100 else "CDR",)
        for i in range(w - 3):
            bit = (raw >> (w - 4 - i)) & 1
            steps += ("CAR" if bit == 0 else "CDR",)
        role = "HEAD" if steps[0] == "CAR" else "TAIL"
        rows.append((w, raw, role, "".join("A" if s == "CAR" else "D" for s in steps)))

if len(rows) != 14:
    raise SystemExit(f"fail-closed: expected 14 selector identities, got {len(rows)}")

lines = [
    "-- GENERATED FROM pinned juv4uk/sens selector_law.rs; DO NOT EDIT.",
    f"-- SENS_COMMIT={commit}",
    "-- This is a mechanical device projection. It is not semantic authority.",
    "",
    "let widths : []i32 = [" + ",".join(str(r[0]) for r in rows) + "]",
    "let payloads : []i32 = [" + ",".join(str(r[1]) for r in rows) + "]",
    "-- role: 1=SelectorHead, 2=SelectorTail; 0=not admitted",
    "let roles : []i32 = [" + ",".join("1" if r[2] == "HEAD" else "2" for r in rows) + "]",
    "",
    "def selector_index (domain: i32) (payload: i32): i32 =",
    "  let matches = map2 (\\w p -> w == domain && p == payload) widths payloads",
    "  let idx = filter (\\i -> matches[i]) (iota (length matches))",
    "  in if length idx == 1 then idx[0] else -1",
    "",
    "entry route_selectors (domains: []i32) (payloads_in: []i32): []i32 =",
    "  map (\\p -> let i = selector_index p.0 p.1",
    "             in if i >= 0 then roles[i] else 0)",
    "",
    "-- expected admitted count: 14; all D6+ identities return 0.",
]
(root / "futhark" / "selector_law.fut").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"generated {len(rows)} selector identities from {commit}")
