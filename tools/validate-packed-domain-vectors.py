#!/usr/bin/env python3
"""Validate mechanical packed-domain kernel vectors without semantic lookup."""

from __future__ import annotations

import json
from pathlib import Path

FIXTURE = Path(__file__).with_name("packed-domain-vectors.json")

def exact_bytes(words):
    bits="".join(words)
    out=[]
    for i in range(0,len(bits),8):
        out.append(int(bits[i:i+8].ljust(8,"0"),2))
    return out,len(bits)

def main():
    data=json.loads(FIXTURE.read_text(encoding="utf-8"))
    failures=[]
    for case in data["positive"]:
        packed,bit_len=exact_bytes(case["source_words"])
        if packed != case["packed_bytes"] or bit_len != case["bit_len"]:
            failures.append(case["id"])
    if failures:
        raise SystemExit("FAIL-CLOSED: " + ", ".join(failures))
    print(f"PACKED-DOMAIN-VECTORS: PASS ({len(data['positive'])} positive cases)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
