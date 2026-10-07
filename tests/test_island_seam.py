#!/usr/bin/env python3
"""Tests for the common execution seam (SENS-BRIDGE, #121).

Runnable with plain python:  python3 tests/test_island_seam.py
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from host.island_seam import Backend, SeamError, WITNESS_SCHEMA  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent.parent


def k_double(payload):
    return payload * 2, "ONE"


def k_split(payload):
    return list(payload), "MANY"


def b_tag(fn, payload):
    obs, mult = fn(payload)
    return {"bridged": obs}, mult


def test_success_path_is_machine_readable():
    b = Backend()
    b.register_kernel("k.double", k_double)
    w = b.island_call("core:opaque-sentinel-do-not-parse", 21, kernel_id="k.double")
    assert w["kind"] == "EXECUTION-WITNESS"
    assert w["schema"] == WITNESS_SCHEMA
    assert w["seam"] == "ISLAND-CALL"
    assert w["status"] == "OK"
    assert w["result_count"] == 1
    assert w["observation"]["multiplicity"] == "ONE"
    json.loads(json.dumps(w))  # machine-readable
    print("ok: success path emits a machine-readable EXECUTION-WITNESS")
    print("   ", json.dumps(w, ensure_ascii=False, sort_keys=True))


def test_semantic_identity_is_echoed_not_interpreted():
    b = Backend()
    b.register_kernel("k.double", k_double)
    sid = "core:opaque-sentinel-do-not-parse"
    w = b.island_call(sid, 1, kernel_id="k.double")
    assert w["semantic_identity"] == sid
    print("ok: opaque semantic identity is echoed verbatim")


def test_many_multiplicity_preserved_and_counted():
    b = Backend()
    b.register_kernel("k.split", k_split)
    w = b.island_call("core:many", [1, 2, 3], kernel_id="k.split")
    assert w["observation"]["multiplicity"] == "MANY"
    assert w["observation"]["native"] == [1, 2, 3]  # producer-native preserved
    assert w["result_count"] == 3                    # derived, not stored
    print("ok: MANY multiplicity preserved; RESULT-COUNT derived =", w["result_count"])


def test_bridge_is_a_resident():
    b = Backend()
    b.register_kernel("k.double", k_double)
    b.register_bridge("b.tag", b_tag)
    w = b.island_call("core:bridged", 5, kernel_id="k.double", bridge_id="b.tag")
    assert w["native"]["bridge"] == "b.tag"
    assert w["observation"]["native"] == {"bridged": 10}
    print("ok: BRIDGE realized as a local resident")


def test_missing_kernel_path():
    b = Backend()
    w = b.island_call("core:absent", 1, kernel_id="k.nope")
    assert w["kind"] == "MISSING-CAPABILITY"
    assert w["capability"] == {"kind": "kernel", "requested": "k.nope"}
    assert w["status"] == "MISSING"
    assert "result_count" not in w  # no result is invented
    json.loads(json.dumps(w))
    print("ok: missing kernel -> typed MISSING-CAPABILITY(kind=kernel)")
    print("   ", json.dumps(w, ensure_ascii=False, sort_keys=True))


def test_missing_bridge_path():
    b = Backend()
    b.register_kernel("k.double", k_double)
    w = b.island_call("core:absent-bridge", 1, kernel_id="k.double", bridge_id="b.nope")
    assert w["kind"] == "MISSING-CAPABILITY"
    assert w["capability"]["kind"] == "bridge"
    print("ok: missing bridge -> typed MISSING-CAPABILITY(kind=bridge)")


def test_bad_multiplicity_fails_closed():
    b = Backend()
    b.register_kernel("k.bad", lambda p: (p, "SOME"))
    try:
        b.island_call("core:bad", 1, kernel_id="k.bad")
    except SeamError:
        print("ok: a kernel returning an unknown multiplicity fails closed")
        return
    raise AssertionError("expected SeamError")


def test_no_core_coordinate_table_in_backend():
    """Acceptance: no Core-coordinate table copied into backend ownership."""
    src = (HERE / "host" / "island_seam.py").read_text(encoding="utf-8")
    for banned in ("varga", "non-varga", "slp1", "iast", "deva", "coordinates", "0x40"):
        assert banned not in src, f"backend leaked Core coordinate data: {banned!r}"
    print("ok: backend holds no Core-coordinate table (seam is identity-agnostic)")


if __name__ == "__main__":
    test_success_path_is_machine_readable()
    test_semantic_identity_is_echoed_not_interpreted()
    test_many_multiplicity_preserved_and_counted()
    test_bridge_is_a_resident()
    test_missing_kernel_path()
    test_missing_bridge_path()
    test_bad_multiplicity_fails_closed()
    test_no_core_coordinate_table_in_backend()
    print("ALL OK")
