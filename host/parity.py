#!/usr/bin/env python3
"""CPU <-> backend parity runner for SENS exact-identity witnesses (#18).

Compares two witness texts in the canonical format that host/cpu_witness.py
emits:

    D<domain>:<bits> <verdict>            # one line per identity
    (cpu-witness (identities N) (rejects R) (sha256 <hex>))

Contract: docs/canonical-boundary.md, section "Next witness" -- the same golden
corpus must run through the CPU and GPU execution paths, and ANY mismatch must
identify the exact (domain, bits) pair that diverged. This runner is that
comparison, and it FAILS CLOSED: a missing line, an extra line, an unknown
verdict, a malformed payload, a missing digest, or a digest disagreement is a
failure -- never a pass.

Comparison is KEYED by (domain, bits), not positional: a single deleted line
must surface as one named missing identity, never as a cascade of shifted
"mismatches" that buries the real divergence.

Usage
-----
    python3 host/parity.py --reference ref.txt --backend gpu.txt
    python3 host/parity.py --self-test
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Dict, Iterable, List, Optional, Tuple

# The key format has ONE source of truth: the CPU oracle. Importing it keeps the
# two sides from drifting; a divergence would be a contract change, not a tweak.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cpu_witness import identity_key  # noqa: E402

# The verdicts the contract names. Anything else fails closed.
NAMED_VERDICTS = ("accept", "reject-domain", "reject-range", "reject-shape")

_IDENT = re.compile(r"^D(\d+):([01]+) (\S+)$")
_DIGEST = re.compile(r"\(sha256 ([0-9a-f]{64})\)")


def parse_witness(text: str):
    """Return (entries, digest, errors). entries are (domain, bits, verdict) in order.

    Every line must be either an identity line or the single summary line.
    Anything unrecognised is an error: parity must not "ignore what it does not
    understand" -- that is exactly how a broken backend would slip through.
    """
    entries: List[Tuple[int, int, str]] = []
    digest: Optional[str] = None
    errors: List[str] = []

    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue

        m = _IDENT.match(line)
        if m:
            width_text = m.group(2)
            domain = int(m.group(1))
            bits = int(width_text, 2)
            verdict = m.group(3)
            if verdict not in NAMED_VERDICTS:
                errors.append(f"line {lineno}: unknown verdict {verdict!r} (fail closed)")
            # identity = (domain, EXACT bits): the payload width is the domain.
            if len(width_text) != domain:
                errors.append(
                    f"line {lineno}: payload width {len(width_text)} != domain {domain}"
                )
            entries.append((domain, bits, verdict))
            continue

        if line.startswith("(") and line.endswith(")"):
            found = _DIGEST.search(line)
            if found:
                if digest is not None:
                    errors.append(f"line {lineno}: second digest line (fail closed)")
                digest = found.group(1)
            else:
                errors.append(f"line {lineno}: summary without a sha256 digest (fail closed)")
            continue

        errors.append(f"line {lineno}: unrecognised line {line!r} (fail closed)")

    if digest is None:
        errors.append("no sha256 digest line (fail closed)")

    return entries, digest, errors


def compare(reference_text: str, backend_text: str):
    """Return (ok, mismatches, reasons, counts). Both sides must agree exactly."""
    ref, ref_digest, ref_err = parse_witness(reference_text)
    bck, bck_digest, bck_err = parse_witness(backend_text)

    mismatches: List[str] = []
    reasons: List[str] = []

    reasons += [f"reference: {e}" for e in ref_err]
    reasons += [f"backend: {e}" for e in bck_err]

    ref_map: Dict[Tuple[int, int], str] = {}
    bck_map: Dict[Tuple[int, int], str] = {}
    for domain, bits, verdict in ref:
        if (domain, bits) in ref_map:
            reasons.append(f"reference repeats {identity_key(domain, bits)} (fail closed)")
        ref_map[(domain, bits)] = verdict
    for domain, bits, verdict in bck:
        if (domain, bits) in bck_map:
            reasons.append(f"backend repeats {identity_key(domain, bits)} (fail closed)")
        bck_map[(domain, bits)] = verdict

    # Keyed, so one missing or extra identity is named once -- not smeared across
    # every following position.
    for key in sorted(set(ref_map) - set(bck_map)):
        reasons.append(
            f"backend missing {identity_key(*key)} (reference says {ref_map[key]!r})"
        )
    for key in sorted(set(bck_map) - set(ref_map)):
        reasons.append(
            f"backend has extra {identity_key(*key)} (backend says {bck_map[key]!r})"
        )

    for key in sorted(set(ref_map) & set(bck_map)):
        if ref_map[key] != bck_map[key]:
            mismatches.append(
                f"({key[0]},{key[1]}) {identity_key(*key)}: "
                f"reference {ref_map[key]!r} vs backend {bck_map[key]!r}"
            )

    if ref_digest != bck_digest:
        reasons.append(f"digest differs: reference {ref_digest}, backend {bck_digest}")

    ok = not mismatches and not reasons
    counts = {"reference": len(ref_map), "backend": len(bck_map)}
    return ok, mismatches, reasons, counts


def _read(path: str) -> Optional[str]:
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        print(f"(parity (unreadable {path}: {exc}) (FAIL))")
        return None


def run(reference_path: str, backend_path: str) -> int:
    reference_text = _read(reference_path)
    backend_text = _read(backend_path)
    if reference_text is None or backend_text is None:
        return 1

    ok, mismatches, reasons, counts = compare(reference_text, backend_text)

    for item in mismatches:
        print(f"mismatch: {item}")
    for item in reasons:
        print(f"fail-closed: {item}")

    verdict = "ok" if ok else "FAIL"
    print(
        f"(parity (reference {counts['reference']}) (backend {counts['backend']}) "
        f"(mismatches {len(mismatches)}) (fail-closed {len(reasons)}) {verdict})"
    )
    return 0 if ok else 1


def _witness_text(lines: List[str]) -> str:
    import hashlib

    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    return "\n".join(lines) + f"\n(cpu-witness (identities {len(lines)}) (rejects 0) (sha256 {digest}))\n"


def self_test() -> int:
    failures = 0

    def check(name: str, got, want) -> None:
        nonlocal failures
        ok = got == want
        failures += 0 if ok else 1
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: {got!r} (want {want!r})")

    base = ["D1:0 accept", "D2:00 accept", "D3:001 accept", "D2:11 reject-range"]
    ref = _witness_text(base)

    # 1. identical -> pass
    ok, mism, why, _ = compare(ref, ref)
    check("identical passes", (ok, mism, why), (True, [], []))

    # 2. one flipped verdict (digest recomputed, as a real backend would) -> fail.
    #    The named pair is the point; a differing digest is also expected, since
    #    the digest is computed over the very lines that changed.
    flipped = _witness_text(
        ["D1:0 accept", "D2:00 accept", "D3:001 accept", "D2:11 accept"]
    )
    ok, mism, why, _ = compare(ref, flipped)
    check("flipped verdict fails", ok, False)
    check(
        "flipped verdict names exactly the pair",
        mism,
        ["(2,3) D2:11: reference 'reject-range' vs backend 'accept'"],
    )
    check("flipped verdict: digest difference reported", any("digest differs" in r for r in why), True)

    # 3. one missing line -> ONE named missing identity, no positional cascade
    truncated = _witness_text(["D1:0 accept", "D2:00 accept", "D3:001 accept"])
    ok, mism, why, _ = compare(ref, truncated)
    check("missing line fails closed", ok, False)
    check("missing line: no positional mismatches", mism, [])
    check(
        "missing line named exactly once",
        [r for r in why if "missing" in r],
        ["backend missing D2:11 (reference says 'reject-range')"],
    )

    # 4. an extra line is named too
    extra = _witness_text(base + ["D1:1 reject-range"])
    ok, mism, why, _ = compare(ref, extra)
    check("extra line fails closed", ok, False)
    check("extra line named", any("has extra D1:1" in r for r in why), True)

    # 5. unknown verdict -> fail closed
    bogus = _witness_text(["D1:0 accept", "D2:00 accept", "D3:001 accept", "D2:11 maybe"])
    ok, mism, why, _ = compare(ref, bogus)
    check("unknown verdict fails closed", ok, False)
    check("unknown verdict named", any("unknown verdict" in r for r in why), True)

    # 6. digest disagreement on identical lines -> fail closed
    good = _witness_text(base)
    bad_digest = good.replace(re.search(r"[0-9a-f]{64}", good).group(0), "0" * 64)
    ok, mism, why, _ = compare(ref, bad_digest)
    check("digest mismatch fails closed", ok, False)
    check("digest mismatch named", any("digest differs" in r for r in why), True)

    # 7. payload width != domain -> fail closed
    wide = _witness_text(["D1:0 accept", "D2:00 accept", "D3:001 accept", "D3:0011 accept"])
    ok, mism, why, _ = compare(ref, wide)
    check("width != domain fails closed", ok, False)

    # 8. an unrecognised line is never ignored
    junk = _witness_text(base).replace("D1:0 accept", "garbage line here")
    ok, mism, why, _ = compare(ref, junk)
    check("unrecognised line fails closed", ok, False)

    # 9. a repeated identity within one side is an error, not a silent last-wins
    dup = _witness_text(["D1:0 accept", "D1:0 reject-range", "D2:00 accept", "D3:001 accept", "D2:11 reject-range"])
    ok, mism, why, _ = compare(ref, dup)
    check("repeated identity fails closed", any("repeats D1:0" in r for r in why), True)

    if failures:
        print(f"(parity-selftest-failed ({failures}))")
        return 1
    print("(parity-selftest-ok)")
    return 0


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference", help="witness produced by the CPU oracle")
    ap.add_argument("--backend", help="witness produced by the backend under test")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(list(argv) if argv is not None else None)

    if args.self_test:
        return self_test()
    if not args.reference or not args.backend:
        ap.error("--reference and --backend are required (or use --self-test)")
    return run(args.reference, args.backend)


if __name__ == "__main__":
    sys.exit(main())
