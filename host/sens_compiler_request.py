#!/usr/bin/env python3
"""Strict transport parser for the canonical SENS compiler-semantic request.

This module consumes facts already derived by SENS. It does not infer a role
from coordinates, widths, names, or legacy identities.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

FORBIDDEN_TARGET_TOKENS = ("cuda", "futhark", "cml", "Sid8", "Sens8")

SENS_ROLE_TO_BACKEND_ROLE = {
    "quote-form": "QuoteForm",
    "atom-predicate": "AtomPredicate",
    "selector-tail": "SelectorTail",
    "selector-head": "SelectorHead",
    "atom-equality": "AtomEquality",
    "cond-form": "CondForm",
    "pair-construct": "PairConstruct",
    "lambda-form": "LambdaForm",
    "define-form": "DefineForm",
}

EXPECTED_ROLE_AUTHORITY_DIGEST = (
    "9768f683e90cfb56ca95675d1f6ac0e6ede91e21cebe97e20b455cf1b3094791"
)
EXPECTED_SOURCE_REPOSITORY = "juv4uk/sens"
EXPECTED_SOURCE_COMMIT = "1c052b75a63a640ded2283a9bc7a164c3eefb114"
EXPECTED_CONTRACT = "11.6"


class SensRequestError(ValueError):
    pass


def _quoted_pair(source: str, key: str) -> str:
    pattern = re.compile(
        rf'\({re.escape(key)}\s+\.\s+("(?:(?:\\.)|[^"\\])*")\)'
    )
    match = pattern.search(source)
    if match is None:
        raise SensRequestError(f"missing quoted compiler request field: {key}")
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise SensRequestError(f"invalid quoted compiler request field: {key}") from exc


def _atom_pair(source: str, key: str) -> str:
    pattern = re.compile(
        rf"\({re.escape(key)}\s+\.\s+([A-Za-z0-9_./-]+)\)"
    )
    match = pattern.search(source)
    if match is None:
        raise SensRequestError(f"missing atom compiler request field: {key}")
    return match.group(1)


def _validate_source_shape(source: str) -> None:
    if not source.lstrip().startswith("(compiler-semantic-request"):
        raise SensRequestError("missing compiler-semantic-request envelope")
    lowered = source.casefold()
    for token in FORBIDDEN_TARGET_TOKENS:
        if token.casefold() in lowered:
            raise SensRequestError(
                f"target/legacy vocabulary leaked into SENS semantic request: {token}"
            )
    if "(mechanism-status . unknown)" not in source:
        raise SensRequestError("SENS request must leave target mechanism status unknown")
    if "(mechanism-ref . ())" not in source:
        raise SensRequestError("SENS request must leave target mechanism reference empty")


def load_sens_request(path: Path) -> dict:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SensRequestError(f"cannot read SENS compiler request: {exc}") from exc

    _validate_source_shape(source)

    schema = _atom_pair(source, "schema")
    if schema != "compiler-semantic-input/1":
        raise SensRequestError(f"unsupported SENS compiler request schema: {schema}")

    fixture_id = _quoted_pair(source, "fixture-id")

    domain = _atom_pair(source, "domain")
    bits = _atom_pair(source, "bits")
    if domain == "D8":
        raise SensRequestError("D8 compiler requests are fail-closed")
    if domain not in {"D1", "D2", "D3", "D4", "D5", "D6", "D7"}:
        raise SensRequestError(f"SENS compiler request domain is not admitted: {domain}")
    expected_width = int(domain[1:])
    if len(bits) != expected_width or any(bit not in "01" for bit in bits):
        raise SensRequestError(
            f"SENS compiler request has invalid {domain} bits: {bits!r}"
        )
    authority_ref = _quoted_pair(source, "authority-ref")
    proof_ref = _quoted_pair(source, "proof-ref")
    semantic_status = _atom_pair(source, "semantic-status")
    if semantic_status != "current":
        raise SensRequestError("SENS compiler request is not current")

    execution_role = _atom_pair(source, "execution-role")
    try:
        backend_role = SENS_ROLE_TO_BACKEND_ROLE[execution_role]
    except KeyError as exc:
        raise SensRequestError(
            f"unknown SENS-owned abstract compiler role: {execution_role}"
        ) from exc

    repository = _quoted_pair(source, "repository")
    if repository != EXPECTED_SOURCE_REPOSITORY:
        raise SensRequestError("unexpected semantic authority repository")

    revision = _quoted_pair(source, "revision")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise SensRequestError("invalid SENS source revision")
    if revision != EXPECTED_SOURCE_COMMIT:
        raise SensRequestError("stale SENS source revision")
    authority_path = _quoted_pair(source, "authority-path")
    authority_sha256 = _quoted_pair(source, "authority-sha256")
    if not re.fullmatch(r"[0-9a-f]{64}", authority_sha256):
        raise SensRequestError("invalid SENS authority digest")
    if authority_sha256 != EXPECTED_ROLE_AUTHORITY_DIGEST:
        raise SensRequestError("stale SENS role authority digest")
    nucleus_sha256 = None
    try:
        candidate = _quoted_pair(source, "compiler-nucleus-sha256")
    except SensRequestError:
        candidate = None
    if candidate is not None:
        if not re.fullmatch(r"[0-9a-f]{64}", candidate):
            raise SensRequestError("invalid compiler nucleus digest")
        nucleus_sha256 = candidate
    contract = _atom_pair(source, "contract")
    if contract != EXPECTED_CONTRACT:
        raise SensRequestError(f"unsupported SENS contract: {contract}")

    return {
        "schema": schema,
        "fixture_id": fixture_id,
        "identity": {"domain": domain, "bits": bits},
        "law": {
            "authority_ref": authority_ref,
            "proof_ref": proof_ref,
            "semantic_status": semantic_status,
        },
        "role": backend_role,
        "sens_role": execution_role,
        "provenance": {
            "source_repository": repository,
            "source_commit": revision,
            "contract": contract,
            "role_authority_digest": authority_sha256,
            "authority_path": authority_path,
            "compiler_nucleus_sha256": nucleus_sha256,
        },
    }

def _matching_list(source: str, open_index: int) -> str:
    """Return one balanced S-expression beginning at open_index."""
    if open_index >= len(source) or source[open_index] != "(":
        raise SensRequestError("compiler artifact semantic-request is not an S-expression")
    depth = 0
    in_string = False
    escaped = False
    for index in range(open_index, len(source)):
        char = source[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return source[open_index:index + 1]
    raise SensRequestError("unterminated compiler semantic request")

def load_sens_artifact(path: Path) -> dict:
    """Load a canonical SENS compiler-compilation-artifact/1 wrapper."""
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SensRequestError(f"cannot read SENS compiler artifact: {exc}") from exc

    if not source.lstrip().startswith("(compilation-artifact"):
        raise SensRequestError("missing compilation-artifact envelope")
    schema = _atom_pair(source, "schema")
    if schema != "compiler-compilation-artifact/1":
        raise SensRequestError(f"unsupported SENS compiler artifact schema: {schema}")

    fixture_id = _quoted_pair(source, "fixture-id")
    digest = _quoted_pair(source, "semantic-request-sha256")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise SensRequestError("invalid semantic request digest")

    marker = "(semantic-request ."
    marker_index = source.find(marker)
    if marker_index < 0:
        raise SensRequestError("missing embedded semantic request")
    request_start = source.find("(", marker_index + len(marker))
    if request_start < 0:
        raise SensRequestError("missing embedded compiler semantic request")
    semantic_request = _matching_list(source, request_start)
    inner_fixture = _quoted_pair(semantic_request, "fixture-id")
    if inner_fixture != fixture_id:
        raise SensRequestError("artifact fixture-id disagrees with embedded request")
    actual_digest = hashlib.sha256(semantic_request.encode("utf-8")).hexdigest()
    if actual_digest != digest:
        raise SensRequestError("semantic request digest mismatch")

    if "(required-capabilities . ())" not in source:
        raise SensRequestError("compiler artifact capabilities are not empty")
    artifact_status = _atom_pair(source, "artifact-status")
    if artifact_status != "canonical-backend-neutral":
        raise SensRequestError("compiler artifact is not canonical backend-neutral")

    return {
        "artifact_schema": schema,
        "fixture_id": fixture_id,
        "semantic_request_sha256": digest,
        "semantic_request": semantic_request,
    }
