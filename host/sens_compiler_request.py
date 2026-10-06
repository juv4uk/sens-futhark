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
EXPECTED_SOURCE_COMMIT = "1869fd5e51f38565ca968abceaa4bc933ae7a114"
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


def _parse_compiler_value(source: str):
    """Parse the canonical artifact S-expression into SENS value shapes.

    The admitted compiler-value kinds are NIL, exact DomainIdentity, Symbol,
    String and Pair (lists are encoded as nested Pairs ending in NIL).
    """
    index = 0

    def skip_ws() -> None:
        nonlocal index
        while index < len(source) and source[index].isspace():
            index += 1

    def parse_string():
        nonlocal index
        start = index - 1
        while index < len(source):
            if source[index] == '"':
                index += 1
                try:
                    return ("string", json.loads(source[start:index]))
                except json.JSONDecodeError as exc:
                    raise SensRequestError("invalid compiler artifact string") from exc
            if source[index] == "\\":
                index += 2
            else:
                index += 1
        raise SensRequestError("unterminated compiler artifact string")

    def parse_expr():
        nonlocal index
        skip_ws()
        if index >= len(source):
            raise SensRequestError("unexpected end of compiler artifact")
        char = source[index]
        if char == '"':
            index += 1
            return parse_string()
        if char == "(":
            index += 1
            skip_ws()
            if index < len(source) and source[index] == ")":
                index += 1
                return ("nil",)

            head = parse_expr()
            skip_ws()
            if index < len(source) and source[index] == ".":
                index += 1
                tail = parse_expr()
                skip_ws()
                if index >= len(source) or source[index] != ")":
                    raise SensRequestError("dotted compiler artifact pair is not closed")
                index += 1
                return ("pair", head, tail)

            items = [head]
            while True:
                skip_ws()
                if index >= len(source):
                    raise SensRequestError("unterminated compiler artifact list")
                if source[index] == ")":
                    index += 1
                    value = ("nil",)
                    for item in reversed(items):
                        value = ("pair", item, value)
                    return value
                items.append(parse_expr())

        start = index
        while index < len(source) and not source[index].isspace() and source[index] not in "()":
            index += 1
        token = source[start:index]
        if not token or token == ".":
            raise SensRequestError("invalid compiler artifact atom")
        if re.fullmatch(r"[01]{1,8}", token):
            return ("domain", len(token), int(token, 2))
        return ("symbol", token)

    value = parse_expr()
    skip_ws()
    if index != len(source):
        raise SensRequestError("trailing data after compiler artifact")
    return value


def _value_head_symbol(value, context: str) -> str:
    if not isinstance(value, tuple) or value[0] != "pair":
        raise SensRequestError(f"{context} is not a proper compiler artifact list")
    head = value[1]
    if not isinstance(head, tuple) or head[0] != "symbol":
        raise SensRequestError(f"{context} head is not a symbol")
    return head[1]


def _as_proper_list(value, context: str):
    items = []
    current = value
    while True:
        if current[0] == "nil":
            return items
        if current[0] != "pair":
            raise SensRequestError(f"{context} is not a proper list")
        items.append(current[1])
        current = current[2]


def _field_map(artifact_value):
    fields = _as_proper_list(artifact_value, "compiler artifact")
    if not fields or not (
        isinstance(artifact_value[1], tuple)
        and artifact_value[1][0] == "symbol"
    ):
        raise SensRequestError("compiler artifact has no envelope symbol")
    if artifact_value[1][1] != "compilation-artifact":
        raise SensRequestError("missing compilation-artifact envelope")

    result = {}
    ordered = []
    for field in fields[1:]:
        if not isinstance(field, tuple) or field[0] != "pair":
            raise SensRequestError("compiler artifact field is not a dotted pair")
        key = field[1]
        if not isinstance(key, tuple) or key[0] != "symbol":
            raise SensRequestError("compiler artifact field name is not a symbol")
        name = key[1]
        if name in result:
            raise SensRequestError(f"duplicate compiler artifact field: {name}")
        result[name] = field[2]
        ordered.append(name)
    return ordered, result


def _symbol_value(value, key: str) -> str:
    if not isinstance(value, tuple) or value[0] != "symbol":
        raise SensRequestError(f"compiler artifact field {key} must be a symbol")
    return value[1]


def _string_value(value, key: str) -> str:
    if not isinstance(value, tuple) or value[0] != "string":
        raise SensRequestError(f"compiler artifact field {key} must be a string")
    return value[1]


def _encode_canonical_compiler_value(value, out: bytearray) -> None:
    kind = value[0]
    if kind == "nil":
        out.append(0x00)
        return
    if kind == "domain":
        out.append(0x01)
        out.append(value[1])
        out.append(value[2])
        return
    if kind == "symbol":
        raw = value[1].encode("utf-8")
        out.append(0x02)
        out.extend(len(raw).to_bytes(8, "little", signed=False))
        out.extend(raw)
        return
    if kind == "string":
        raw = value[1].encode("utf-8")
        out.append(0x03)
        out.extend(len(raw).to_bytes(8, "little", signed=False))
        out.extend(raw)
        return
    if kind == "pair":
        out.append(0x04)
        _encode_canonical_compiler_value(value[1], out)
        _encode_canonical_compiler_value(value[2], out)
        return
    raise SensRequestError(
        f"unsupported compiler artifact value kind in canonical digest: {kind}"
    )


def _canonical_value_sha256(value) -> str:
    encoded = bytearray()
    _encode_canonical_compiler_value(value, encoded)
    return hashlib.sha256(encoded).hexdigest()


def load_sens_whole_program_artifact(
    path: Path,
    *,
    program_wire: bytes | None = None,
) -> dict:
    """Load the canonical SENS whole-program compiler-compilation-artifact/1.

    SENS chooses the semantic-request sequence and its digest. This consumer
    verifies the exact representation-only digest and provenance envelope; it
    never walks program nodes or reconstructs semantic requests.
    """
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SensRequestError(
            f"cannot read SENS whole-program artifact: {exc}"
        ) from exc

    if not source.lstrip().startswith("(compilation-artifact"):
        raise SensRequestError("missing compilation-artifact envelope")

    value = _parse_compiler_value(source)
    ordered, fields = _field_map(value)
    expected_order = [
        "schema",
        "artifact-kind",
        "program-wire-sha256",
        "semantic-requests-sha256",
        "authority-provenance",
        "semantic-requests",
        "required-capabilities",
        "artifact-status",
    ]
    if ordered != expected_order:
        raise SensRequestError(
            "whole-program compiler artifact field order/shape is not canonical"
        )

    schema = _symbol_value(fields["schema"], "schema")
    if schema != "compiler-compilation-artifact/1":
        raise SensRequestError(
            f"unsupported SENS compiler artifact schema: {schema}"
        )

    artifact_kind = _symbol_value(fields["artifact-kind"], "artifact-kind")
    if artifact_kind != "whole-program":
        raise SensRequestError("compiler artifact is not whole-program")

    program_wire_sha256 = _string_value(
        fields["program-wire-sha256"], "program-wire-sha256"
    )
    if not re.fullmatch(r"[0-9a-f]{64}", program_wire_sha256):
        raise SensRequestError("invalid program-wire-sha256")
    if program_wire is not None:
        actual_program_sha256 = hashlib.sha256(program_wire).hexdigest()
        if actual_program_sha256 != program_wire_sha256:
            raise SensRequestError("program wire digest mismatch")

    semantic_requests_sha256 = _string_value(
        fields["semantic-requests-sha256"], "semantic-requests-sha256"
    )
    if not re.fullmatch(r"[0-9a-f]{64}", semantic_requests_sha256):
        raise SensRequestError("invalid semantic-requests-sha256")

    actual_semantic_requests_sha256 = _canonical_value_sha256(
        fields["semantic-requests"]
    )
    if actual_semantic_requests_sha256 != semantic_requests_sha256:
        raise SensRequestError("semantic requests digest mismatch")

    provenance = _as_proper_list(
        fields["authority-provenance"], "authority-provenance"
    )
    if len(provenance) != 5:
        raise SensRequestError("authority-provenance must contain exactly 5 values")
    provenance_values = []
    for index, item in enumerate(provenance):
        if not isinstance(item, tuple) or item[0] != "string":
            raise SensRequestError(
                f"authority-provenance value {index} must be a string"
            )
        provenance_values.append(item[1])

    sens_revision, authority_path, authority_sha256, contract, nucleus_sha256 = (
        provenance_values
    )
    if sens_revision != "5964c4dd2378364a5307b143a65438f8609fecd6":
        raise SensRequestError("stale SENS whole-program revision")
    if authority_path != "language-contract.lisp":
        raise SensRequestError("unexpected SENS compiler authority path")
    if authority_sha256 != EXPECTED_ROLE_AUTHORITY_DIGEST:
        raise SensRequestError("stale SENS compiler authority digest")
    if contract != EXPECTED_CONTRACT:
        raise SensRequestError("unsupported SENS compiler contract")
    if not re.fullmatch(r"[0-9a-f]{64}", nucleus_sha256):
        raise SensRequestError("invalid compiler-nucleus source digest")

    if fields["required-capabilities"][0] != "nil":
        raise SensRequestError("whole-program artifact capabilities must be empty")

    artifact_status = _symbol_value(fields["artifact-status"], "artifact-status")
    if artifact_status != "canonical-backend-neutral":
        raise SensRequestError("compiler artifact is not canonical backend-neutral")

    return {
        "artifact_schema": schema,
        "artifact_kind": artifact_kind,
        "program_wire_sha256": program_wire_sha256,
        "semantic_requests_sha256": semantic_requests_sha256,
        "semantic_requests": fields["semantic-requests"],
        "authority_provenance": {
            "sens_revision": sens_revision,
            "authority_path": authority_path,
            "authority_sha256": authority_sha256,
            "contract": contract,
            "compiler_nucleus_sha256": nucleus_sha256,
        },
        "required_capabilities": (),
        "artifact_status": artifact_status,
    }

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
