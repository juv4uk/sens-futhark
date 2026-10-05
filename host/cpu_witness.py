#!/usr/bin/env python3
"""CPU reference witness for exact SENS identities (#3).

Reads the canonical fixture (domain, width, bits, exact_text) and produces a
deterministic witness. There is NO semantics here: an identity is
`(domain, exact bits)`, validated against the contract's exact widths. GPU
results are compared to THIS, not the other way round.

Contract: docs/canonical-boundary.md
  - identity = (domain, exact bits); equal packed payloads do NOT collapse
    across domains (`D1:1` and `D3:001` are distinct);
  - D1..D7 are current; D8 is research / fail-closed;
  - a domain of width w has exactly 2**w identities, bits in [0, 2**w);
  - the physical carrier width is never the semantic width.

Usage
-----
    python3 host/cpu_witness.py --fixture tests/identity_vectors.csv
    python3 host/cpu_witness.py --self-test
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from typing import Iterable, List, Sequence, Tuple

# D1..D7 are current. D8 is research and must fail closed, so it is NOT here:
# admission is a decision upstream, never inferred from a domain number.
CURRENT_DOMAINS = (1, 2, 3, 4, 5, 6, 7)


def limit(domain: int) -> int:
    """Exact number of identities a current domain admits: 2**width."""
    return 1 << domain if domain in CURRENT_DOMAINS else 0


def identity_key(domain: int, bits: int) -> str:
    """Canonical identity text: the domain plus its exact bit payload.

    The payload is padded to the domain's exact width, so the key carries the
    domain, not just the number: `D1:1` and `D3:001` cannot collide.
    """
    return f"D{domain}:{bits:0{domain}b}" if domain > 0 else f"D{domain}:?"


def verdict(domain: int, bits: int) -> str:
    """Named verdict for one identity. Never guesses; anything unknown fails closed."""
    if domain not in CURRENT_DOMAINS:
        return "reject-domain"          # D0, D8, anything else: not admitted here
    if bits < 0 or bits >= limit(domain):
        return "reject-range"           # outside the domain's exact capacity
    return "accept"


def load_fixture(path: str) -> List[Tuple[int, int, int, str]]:
    rows: List[Tuple[int, int, int, str]] = []
    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(line for line in handle if not line.lstrip().startswith("#")):
            rows.append((int(row["domain"]), int(row["width"]), int(row["bits"]), row["exact_text"]))
    return rows


def witness(rows: Sequence[Tuple[int, int, int, str]]) -> Tuple[List[str], str]:
    """Deterministic witness: one line per identity, plus a digest over the lines."""
    lines = []
    for domain, width, bits, exact_text in rows:
        # the fixture's own width column must agree with the domain, and the
        # text must be the exact payload: a mismatch is a fixture defect, named.
        shape_ok = (width == domain) and (exact_text == format(bits, f"0{width}b"))
        v = verdict(domain, bits) if shape_ok else "reject-shape"
        lines.append(f"{identity_key(domain, bits)} {v}")
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    return lines, digest


def self_test() -> int:
    failures = 0

    def check(name: str, got, want) -> None:
        nonlocal failures
        ok = got == want
        failures += 0 if ok else 1
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: {got!r} (want {want!r})")

    # D1..D8 boundaries: 0 and limit-1 accept, limit rejects; D0/D8 fail closed
    for d in CURRENT_DOMAINS:
        check(f"D{d}:0", verdict(d, 0), "accept")
        check(f"D{d}:limit-1", verdict(d, limit(d) - 1), "accept")
        check(f"D{d}:limit", verdict(d, limit(d)), "reject-range")
    check("D0", verdict(0, 0), "reject-domain")
    check("D8 (fail-closed)", verdict(8, 0), "reject-domain")

    # cross-domain non-collision: equal packed payload, different identity
    check("D1:1 != D3:001", identity_key(1, 1) == identity_key(3, 1), False)
    check("D2:3 != D4:0011", identity_key(2, 3) == identity_key(4, 3), False)
    check("D5:31 != D6:011111", identity_key(5, 31) == identity_key(6, 31), False)

    # the digest is stable across runs
    rows = [(d, d, b, format(b, f"0{d}b")) for d in CURRENT_DOMAINS for b in range(limit(d))]
    _, a = witness(rows)
    _, b = witness(rows)
    check("digest stable", a == b, True)

    if failures:
        print(f"cpu-witness-selftest-failed ({failures})")
        return 1
    print("(cpu-witness-selftest-ok)")
    return 0


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture", help="canonical identity fixture CSV")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(list(argv) if argv is not None else None)

    if args.self_test:
        return self_test()
    if not args.fixture:
        ap.error("--fixture is required (or use --self-test)")

    rows = load_fixture(args.fixture)
    lines, digest = witness(rows)
    for line in lines:
        print(line)
    rejects = [l for l in lines if not l.endswith(" accept")]
    print(f"(cpu-witness (identities {len(lines)}) (rejects {len(rejects)}) (sha256 {digest}))")
    return 1 if rejects else 0


if __name__ == "__main__":
    sys.exit(main())
