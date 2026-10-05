#!/usr/bin/env python3
"""GPU-native arena for SENS objects — host-side reference (#98, stage S1).

Struct-of-arrays representation: the same layout the CUDA kernel will mirror, so
the device ops (cons / car / cdr / dispatch) can be checked against this
reference. Pure numpy; no GPU needed here.

Node layout (node_bytes per node):
    tag    u8   0=free 1=atom 2=pair
    domain u32  exact-domain code (opaque to the arena; used as the dispatch key)
    left   u32  pair left  / unused
    right  u32  pair right / unused
    value  i64  atom value / unused
"""
from __future__ import annotations

import numpy as np

try:
    from host.arena_layout import NODE_FIELDS
except ImportError:  # running as a script
    import pathlib
    import sys

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
    from host.arena_layout import NODE_FIELDS

FREE, ATOM, PAIR = 0, 1, 2


class ArenaError(Exception):
    """Raised on an invalid arena operation (fail-closed, never silent)."""


class Arena:
    """A fixed-capacity, struct-of-arrays object arena."""

    def __init__(self, capacity: int, node_bytes: int = 24):
        if capacity <= 0:
            raise ArenaError("capacity must be positive")
        self.capacity = int(capacity)
        self.node_bytes = int(node_bytes)
        self.tag = np.zeros(self.capacity, dtype=np.uint8)
        self.domain = np.zeros(self.capacity, dtype=np.uint32)
        self.left = np.zeros(self.capacity, dtype=np.uint32)
        self.right = np.zeros(self.capacity, dtype=np.uint32)
        self.value = np.zeros(self.capacity, dtype=np.int64)
        self._free = list(range(self.capacity - 1, -1, -1))
        self.high_water = 0
        self.selector: dict[int, int] = {}

    # ---- allocation -------------------------------------------------
    def _take(self) -> int:
        if not self._free:
            raise ArenaError("arena full")
        i = self._free.pop()
        if i + 1 > self.high_water:
            self.high_water = i + 1
        return i

    def alloc_atom(self, value: int, domain: int) -> int:
        i = self._take()
        self.tag[i], self.value[i], self.domain[i] = ATOM, value, domain
        self.left[i] = self.right[i] = 0
        return i

    def alloc_pair(self, l: int, r: int, domain: int) -> int:
        i = self._take()
        self.tag[i], self.left[i], self.right[i], self.domain[i] = PAIR, l, r, domain
        self.value[i] = 0
        return i

    def free(self, i: int) -> None:
        if self.tag[i] == FREE:
            return
        self.tag[i] = FREE
        self._free.append(i)

    # ---- O(1) array accessors --------------------------------------
    def car(self, i: int) -> int:
        if self.tag[i] != PAIR:
            raise ArenaError(f"car of non-pair at {i}")
        return int(self.left[i])

    def cdr(self, i: int) -> int:
        if self.tag[i] != PAIR:
            raise ArenaError(f"cdr of non-pair at {i}")
        return int(self.right[i])

    def atom_value(self, i: int) -> int:
        if self.tag[i] != ATOM:
            raise ArenaError(f"value of non-atom at {i}")
        return int(self.value[i])

    def domain_of(self, i: int) -> int:
        return int(self.domain[i])

    # ---- minimal dispatch (selector-law tables are stage S2) --------
    def register(self, domain: int, handler_id: int) -> None:
        self.selector[int(domain)] = int(handler_id)

    def dispatch(self, i: int):
        return self.selector.get(int(self.domain[i]))

    # ---- mark & compact --------------------------------------------
    def mark(self, roots) -> set:
        seen: set[int] = set()
        stack = list(roots)
        while stack:
            i = stack.pop()
            if i in seen or i < 0 or i >= self.capacity or self.tag[i] == FREE:
                continue
            seen.add(i)
            if self.tag[i] == PAIR:
                stack.append(int(self.left[i]))
                stack.append(int(self.right[i]))
        return seen

    def compact(self, roots):
        """Slide reachable nodes to a dense prefix; rewrite pointers.

        Returns (new_roots, live_count). Frees the tail for reuse.
        """
        live = sorted(self.make(roots))
        remap = {old: new for new, old in enumerate(live)}
        for new, old in enumerate(live):
            if new != old:
                self.tag[new], self.domain[new] = self.tag[old], self.domain[old]
                self.left[new], self.right[new] = self.left[old], self.right[old]
                self.value[new] = self.value[old]
        for new in range(len(live)):
            if self.tag[new] == PAIR:
                self.left[new] = remap[int(self.left[new])]
                self.right[new] = remap[int(self.right[new])]
        for i in range(len(live), self.high_water):
            self.tag[i] = FREE
        self.high_water = len(live)
        self._free = list(range(self.capacity - 1, len(live) - 1, -1))
        return [remap[r] for r in roots], len(live)

    # ---- accounting -------------------------------------------------
    def used_bytes(self) -> int:
        return self.high_water * self.node_bytes

    def spare_bytes(self) -> int:
        return (self.capacity - self.high_water) * self.node_bytes

    # ---- host -> device packing ------------------------------------
    def to_buffers(self) -> dict:
        """The SoA buffers exactly as the device receives them (flat, packed)."""
        return {
            "fields": tuple(name for name, *_ in NODE_FIELDS),
            "tag": self.tag,
            "domain": self.domain,
            "left": self.left,
            "right": self.right,
            "value": self.value,
            "capacity": self.capacity,
            "high_water": self.high_water,
            "node_bytes": self.node_bytes,
        }

    @classmethod
    def from_buffers(cls, bufs: dict) -> "Arena":
        a = cls(int(bufs["capacity"]), node_bytes=int(bufs.get("node_bytes", 24)))
        a.tag = np.array(bufs["tag"], dtype=np.uint8)
        a.domain = np.array(bufs["domain"], dtype=np.uint32)
        a.left = np.array(bufs["left"], dtype=np.uint32)
        a.right = np.array(bufs["right"], dtype=np.uint32)
        a.value = np.array(bufs["value"], dtype=np.int64)
        a.high_water = int(bufs["high_water"])
        a._free = [i for i in range(a.capacity - 1, -1, -1) if a.tag[i] == FREE]
        return a
