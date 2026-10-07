#!/usr/bin/env python3
"""The common execution seam (SENS-BRIDGE, #121; SENS D10 authority: sens#4126).

This repository is a BACKEND / MECHANISM owner. It must NOT mint Core
semantic identities from backend-native operations. It adopts only the
common seam:

    ISLAND-CALL   EXECUTION-WITNESS   NATIVE-OBSERVATION
    RESULT-COUNT  BRIDGE              MISSING-CAPABILITY

A semantic identity arrives opaque; the backend never interprets or
renumbers it. The backend answers with an EXECUTION-WITNESS describing
the *realized mechanism* (local bridge/kernel ids), preserving the
producer-native observation and its multiplicity. If the requested
capability is absent it answers with a typed MISSING-CAPABILITY.

Derived at Core level, so NOT separate residents here:
  ZERO/ONE/MANY results        -> RESULT-COUNT (computed)
  MISSING-KERNEL / MISSING-BRIDGE -> MISSING-CAPABILITY(kind)
"""
from __future__ import annotations

WITNESS_SCHEMA = "island-witness/v1"
CAPABILITY_KINDS = ("kernel", "bridge")
MULTIPLICITIES = ("ZERO", "ONE", "MANY")


class SeamError(Exception):
    """Raised when a backend violates the seam contract."""


def _result_count(multiplicity: str, observation) -> int:
    """RESULT-COUNT is *derived* from multiplicity, never a separate resident."""
    if multiplicity == "ZERO":
        return 0
    if multiplicity == "ONE":
        return 1
    if multiplicity == "MANY":
        if not isinstance(observation, (list, tuple)):
            raise SeamError("MANY multiplicity requires a sequence observation")
        return len(observation)
    raise SeamError(f"unknown multiplicity {multiplicity!r}")


class Backend:
    """A backend that adopts the common seam. Native identities stay local."""

    def __init__(self, name: str = "sens-futhark"):
        self.name = name
        self._kernels = {}   # local kernel id -> callable(payload) -> (observation, multiplicity)
        self._bridges = {}   # local bridge id -> callable(kernel_fn, payload) -> (observation, multiplicity)

    # --- registration: local identities only ---
    def register_kernel(self, kernel_id: str, fn) -> None:
        self._kernels[kernel_id] = fn

    def register_bridge(self, bridge_id: str, fn) -> None:
        self._bridges[bridge_id] = fn

    # --- the island boundary ---
    def island_call(self, semantic_identity, payload, kernel_id, bridge_id=None):
        """Accept an opaque semantic identity + native payload; answer with a witness."""
        if kernel_id not in self._kernels:
            return self._missing("kernel", kernel_id, semantic_identity)
        if bridge_id is not None and bridge_id not in self._bridges:
            return self._missing("bridge", bridge_id, semantic_identity)

        fn = self._kernels[kernel_id]
        if bridge_id is not None:
            observation, multiplicity = self._bridges[bridge_id](fn, payload)
        else:
            observation, multiplicity = fn(payload)

        if multiplicity not in MULTIPLICITIES:
            raise SeamError(f"kernel {kernel_id} returned bad multiplicity {multiplicity!r}")

        return {
            "kind": "EXECUTION-WITNESS",
            "schema": WITNESS_SCHEMA,
            "seam": "ISLAND-CALL",
            "semantic_identity": semantic_identity,   # echoed, never interpreted
            "backend": self.name,
            "native": {"kernel": kernel_id, "bridge": bridge_id},
            "observation": {"native": observation, "multiplicity": multiplicity},
            "result_count": _result_count(multiplicity, observation),
            "status": "OK",
        }

    def _missing(self, kind, requested, semantic_identity):
        assert kind in CAPABILITY_KINDS, kind
        return {
            "kind": "MISSING-CAPABILITY",
            "schema": WITNESS_SCHEMA,
            "seam": "ISLAND-CALL",
            "semantic_identity": semantic_identity,
            "backend": self.name,
            "capability": {"kind": kind, "requested": requested},
            "status": "MISSING",
        }
