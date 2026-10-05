#!/usr/bin/env python3
"""Validate and select the Futhark lowering for compiler-backend/v1.

This module never derives SENS meaning. The role and GPU admission arrive as
already-verified upstream facts; this host component only chooses a target
mechanism for the backend implementation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "futhark" / "compiler_structural.fut"

# These are provenance facts, not semantic meaning. They change only when the
# upstream compiler-authority bundle changes.
EXPECTED_SOURCE_COMMIT = "08db33ced8643aedaa7de35cb61407900c0b0c05"
EXPECTED_ROLE_AUTHORITY_DIGEST = "a4d914073bc1a26f3721d404ac74894b99fe057159da76346ad2092a771bdfc9"

ROLE_TO_ENTRY = {
    "PairConstruct": "lower_pair_construct",
    "SelectorHead": "lower_selector_head",
    "SelectorTail": "lower_selector_tail",
}


class ContractError(ValueError):
    pass


def digest_json(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load_request(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"invalid compiler-backend request: {exc}") from exc

    if data.get("schema") != "sens-futhark/compiler-backend/v1":
        raise ContractError("unsupported compiler-backend schema")

    provenance = data.get("provenance")
    if not isinstance(provenance, dict):
        raise ContractError("missing provenance")
    if provenance.get("source_repository") != "juv4uk/sens":
        raise ContractError("unexpected semantic authority repository")

    commit = provenance.get("source_commit", "")
    if not isinstance(commit, str) or len(commit) != 40:
        raise ContractError("invalid source_commit")
    if commit != EXPECTED_SOURCE_COMMIT:
        raise ContractError("stale provenance: source_commit is not the pinned SENS compiler point")

    if provenance.get("contract") != "11.6":
        raise ContractError("unsupported SENS contract")

    authority = provenance.get("role_authority_digest", "")
    if authority != EXPECTED_ROLE_AUTHORITY_DIGEST:
        raise ContractError("stale provenance: role_authority_digest does not match the pinned SENS authority")

    role = data.get("role")
    if role not in {
        "QuoteForm", "AtomPredicate", "SelectorTail", "SelectorHead",
        "AtomEquality", "CondForm", "PairConstruct", "LambdaForm", "DefineForm"
    }:
        raise ContractError("unknown backend-neutral compiler role")

    admission = data.get("admission")
    if not isinstance(admission, dict) or admission.get("gpu") is not True:
        raise ContractError("GPU admission must be an explicit upstream fact")
    mechanism = admission.get("mechanism")
    if not isinstance(mechanism, str) or not mechanism:
        raise ContractError("missing admitted target mechanism")

    payload = data.get("payload")
    if not isinstance(payload, dict):
        raise ContractError("missing payload")
    left = payload.get("left")
    right = payload.get("right")
    if not isinstance(left, list) or not isinstance(right, list):
        raise ContractError("payload arrays are required")
    if role == "PairConstruct" and len(left) != len(right):
        raise ContractError("pair construction requires equal-length operands")

    return data


def lower(request: dict) -> dict:
    role = request["role"]
    entry = ROLE_TO_ENTRY.get(role)
    if entry is None:
        raise ContractError(f"BLOCKED-MECHANISM: no Futhark lowering for {role}")
    return {
        "schema": "sens-futhark/compiler-backend/v1",
        "target": "futhark",
        "program": str(PROGRAM.relative_to(ROOT)),
        "entry": entry,
        "source_commit": request["provenance"]["source_commit"],
        "role": role,
        "mechanism": request["admission"]["mechanism"],
        "request_digest": digest_json(request),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("request", type=Path)
    parser.add_argument("--lower", action="store_true")
    args = parser.parse_args()

    try:
        request = load_request(args.request)
        result = lower(request) if args.lower else {
            "valid": True,
            "request_digest": digest_json(request),
        }
    except ContractError as exc:
        print(f"FAIL-CLOSED: {exc}")
        return 2

    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
