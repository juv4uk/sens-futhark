"""Only physical SoA/AoS layout evidence; SENS semantics are never authored here."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from host.arena_layout import NODE_FIELDS, block_offsets, layout


def test_candidate_memory_cost_is_derived_from_field_widths():
    candidate = layout()
    assert candidate["packed_bytes"] == sum(field[2] for field in NODE_FIELDS)
    assert candidate["packed_bytes"] == 21
    assert candidate["struct_bytes"] == 24
    assert candidate["offsets"] == {
        "tag": 0, "domain": 4, "left": 8, "right": 12, "value": 16
    }


def test_soa_offsets_preserve_exact_capacity():
    for capacity in (1, 8, 64):
        blocks = block_offsets(capacity=capacity)
        assert blocks["total_bytes"] == capacity * layout()["packed_bytes"]
        assert blocks["offsets"]["tag"] == 0
        assert blocks["offsets"]["domain"] == capacity
        assert blocks["offsets"]["left"] == capacity * 5
        assert blocks["offsets"]["right"] == capacity * 9
        assert blocks["offsets"]["value"] == capacity * 13
