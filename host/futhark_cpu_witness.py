#!/usr/bin/env python3
"""Run the canonical Futhark identity witness on a CPU backend and compare its
semantic observation with the host oracle (#11).

The repository ships two independent implementations of the same mechanical
contract (docs/canonical-boundary.md):

  * host/cpu_witness.py          -- the Python reference oracle;
  * futhark/identity_witness.fut -- the Futhark witness.

This runner executes the Futhark witness on a SEQUENTIAL CPU BACKEND that needs
no GPU and no C compiler -- the Futhark interpreter (`futhark eval`) or the
`python` backend -- over the SHARED corpus (never hand-copied expected outputs;
see docs/cpu-gpu-parity.md), and compares the SEMANTIC observation (accepted vs
rejected) with the host oracle. Any divergence names the exact (domain, bits)
pair.

The GPU lane (#6 / #11) is out of scope here and is NOT claimed. The canonical
`c` backend needs a C compiler, which this environment does not have, so the
backend actually used is recorded in the evidence line.

Shape is a FIXTURE concern, not a witness input: the Futhark witness receives
(domain, bits) only. A fixture row whose own width/exact_text disagree with its
domain is therefore reported separately as "not comparable" rather than as a
witness divergence.

Usage
-----
    python3 host/futhark_cpu_witness.py --fixture tests/identity_vectors.csv
    python3 host/futhark_cpu_witness.py --fixture tests/identity_invalid_vectors.csv
    python3 host/futhark_cpu_witness.py --self-test
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from typing import Iterable, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cpu_witness import load_fixture, verdict as host_verdict, identity_key  # noqa: E402

DEFAULT_WITNESS = "futhark/identity_witness.fut"

# Cross-domain probes for #11 item 3: equal packed payload, different domain ->
# the witness must report them NOT equal. The last entry is a same-domain
# control, which must report equal.
CROSS_DOMAIN_PROBES: List[Tuple[Tuple[int, int], Tuple[int, int], bool]] = [
    ((1, 1), (3, 1), False),     # D1:1 vs D3:001 -- distinct identities
    ((2, 3), (4, 3), False),     # D2:11 vs D4:0011
    ((5, 31), (6, 31), False),   # D5:11111 vs D6:011111
    ((3, 7), (3, 7), True),      # control: identical -> equal
]


def futhark_bin(explicit: Optional[str]) -> str:
    for cand in (explicit, os.environ.get("FUTHARK"), "futhark"):
        if cand:
            return cand
    return "futhark"


def futhark_version(futhark: str) -> str:
    try:
        out = subprocess.run([futhark, "--version"], capture_output=True, text=True, timeout=60)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip().splitlines()[0]
    except Exception as exc:  # noqa: BLE001
        return f"unavailable ({exc.__class__.__name__})"
    return "unknown"


def futhark_eval(futhark: str, witness: str, expr: str) -> str:
    """Evaluate one Futhark expression with the interpreter. No C compiler needed."""
    proc = subprocess.run(
        [futhark, "eval", "-f", witness, expr],
        capture_output=True, text=True, timeout=180,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"futhark eval failed (exit {proc.returncode}): {proc.stderr.strip()[:400]}"
        )
    return proc.stdout.strip()


def parse_bool_list(text: str) -> List[bool]:
    s = text.strip()
    if not (s.startswith("[") and s.endswith("]")):
        raise ValueError(f"not a Futhark list: {text!r}")
    inner = s[1:-1].strip()
    if not inner:
        return []
    return [tok.strip() == "true" for tok in inner.split(",")]


def compare(rows: Sequence[Tuple[int, int, int, str]], futhark_bools: Sequence[bool]):
    """Compare the Futhark witness observation with the host oracle, semantically.

    Returns (mismatches, reasons, not_comparable). The observation compared is
    accepted-vs-rejected, exactly as #11 words it ("compare the semantic
    observation, not physical representation").
    """
    mismatches: List[str] = []
    reasons: List[str] = []
    not_comparable: List[str] = []

    if len(rows) != len(futhark_bools):
        reasons.append(
            f"count differs: fixture {len(rows)}, futhark {len(futhark_bools)} (fail closed)"
        )
        return mismatches, reasons, not_comparable

    for (domain, width, bits, exact_text), futhark_accepts in zip(rows, futhark_bools):
        shape_ok = (width == domain) and (exact_text == format(bits, f"0{width}b"))
        if not shape_ok:
            # Shape is not an input to the witness -- report apart, do not call
            # it a divergence.
            not_comparable.append(f"({domain},{bits}) width={width} text={exact_text!r}")
            continue
        host_v = host_verdict(domain, bits)
        host_accepts = host_v == "accept"
        if host_accepts != futhark_accepts:
            futhark_v = "accept" if futhark_accepts else "reject"
            mismatches.append(
                f"({domain},{bits}) {identity_key(domain, bits)}: "
                f"host {host_v!r} vs futhark {futhark_v!r}"
            )
    return mismatches, reasons, not_comparable


def run(fixture: str, futhark: str, witness: str, emit: bool) -> int:
    rows = load_fixture(fixture)
    domains = [r[0] for r in rows]
    bits = [r[2] for r in rows]

    expr = f"validate_samples [{','.join(map(str, domains))}] [{','.join(map(str, bits))}]"
    futhark_bools = parse_bool_list(futhark_eval(futhark, witness, expr))

    mismatches, reasons, not_comparable = compare(rows, futhark_bools)

    if emit:
        for (domain, _w, b, _t), ok in zip(rows, futhark_bools):
            print(f"{identity_key(domain, b)} {'accept' if ok else 'reject'}")

    # #11 item 3: cross-domain non-collision, run through the witness itself.
    probes = CROSS_DOMAIN_PROBES
    eexpr = (
        f"equal_samples "
        f"[{','.join(str(p[0][0]) for p in probes)}] "
        f"[{','.join(str(p[0][1]) for p in probes)}] "
        f"[{','.join(str(p[1][0]) for p in probes)}] "
        f"[{','.join(str(p[1][1]) for p in probes)}]"
    )
    try:
        eq_bools = parse_bool_list(futhark_eval(futhark, witness, eexpr))
    except Exception as exc:  # noqa: BLE001
        eq_bools = []
        reasons.append(f"cross-domain probe failed: {exc}")

    for (a, b, want), got in zip(probes, eq_bools):
        if got != want:
            mismatches.append(
                f"cross-domain {identity_key(*a)} vs {identity_key(*b)}: "
                f"witness says {'equal' if got else 'not equal'} "
                f"(want {'equal' if want else 'not equal'})"
            )

    for item in not_comparable:
        print(f"note (shape invalid, not a witness input): {item}")
    for item in mismatches:
        print(f"mismatch: {item}")
    for item in reasons:
        print(f"fail-closed: {item}")

    ok = not mismatches and not reasons
    print(
        f"(futhark-cpu-witness (fixture {len(rows)}) "
        f"(comparable {len(rows) - len(not_comparable)}) "
        f"(backend {futhark_version(futhark)}) "
        f"(cross-domain {len(eq_bools)}/{len(probes)}) "
        f"(mismatches {len(mismatches)}) (fail-closed {len(reasons)}) {'ok' if ok else 'FAIL'})"
    )
    return 0 if ok else 1


def self_test() -> int:
    failures = 0

    def check(name: str, got, want) -> None:
        nonlocal failures
        ok = got == want
        failures += 0 if ok else 1
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: {got!r} (want {want!r})")

    check("parse bools", parse_bool_list("[true, false, true]"), [True, False, True])
    check("parse empty", parse_bool_list("[]"), [])

    rows = [(1, 1, 0, "0"), (2, 2, 3, "11"), (3, 3, 8, "1000")]

    # agreement -> no mismatch
    mism, why, nc = compare(rows, [True, True, False])
    check("agreement", (mism, why, nc), ([], [], []))

    # one divergence -> named pair, no cascade
    mism, why, nc = compare(rows, [True, False, False])
    check("divergence named", mism, ["(2,3) D2:11: host 'accept' vs futhark 'reject'"])

    # count mismatch -> fail closed
    mism, why, nc = compare(rows, [True, True])
    check("count mismatch fails closed", bool(why), True)

    # D8 fail-closed: host rejects, witness must reject
    mism, why, nc = compare([(8, 8, 0, "00000000")], [False])
    check("D8 both reject", (mism, why, nc), ([], [], []))
    mism, why, nc = compare([(8, 8, 0, "00000000")], [True])
    check("D8 witness wrongly accepts", bool(mism), True)

    # shape-invalid row is reported apart, never as a divergence
    mism, why, nc = compare([(3, 2, 1, "01")], [True])
    check("shape-invalid noted, not a mismatch", (mism, why, len(nc)), ([], [], 1))

    if failures:
        print(f"(futhark-cpu-witness-selftest-failed ({failures}))")
        return 1
    print("(futhark-cpu-witness-selftest-ok)")
    return 0


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture", help="canonical identity fixture CSV")
    ap.add_argument("--futhark", help="path to the futhark binary (default: $FUTHARK or PATH)")
    ap.add_argument("--witness", default=DEFAULT_WITNESS, help="Futhark witness source")
    ap.add_argument("--emit", action="store_true", help="print the Futhark witness lines")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(list(argv) if argv is not None else None)

    if args.self_test:
        return self_test()
    if not args.fixture:
        ap.error("--fixture is required (or use --self-test)")
    return run(args.fixture, futhark_bin(args.futhark), args.witness, args.emit)


if __name__ == "__main__":
    sys.exit(main())
