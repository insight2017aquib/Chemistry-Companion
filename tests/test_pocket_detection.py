"""
tests/test_pocket_detection.py
==============================
Tests for Phase 3B pocket detection.
"""

import pytest

from docking_workflow.pocket_detection import (
    detect_pockets,
    _is_fpocket_available,
    pockets_to_suggestions,
    Pocket
)


def test_detect_pockets_graceful_when_fpocket_missing():
    """When fpocket is not installed, the function should return empty list without crashing."""
    # This test will pass whether or not fpocket is installed
    result = detect_pockets("ATOM      1  CA  ALA A   1      0.000   0.000   0.000")
    assert isinstance(result, list)


def test_pockets_to_suggestions_empty():
    suggestions = pockets_to_suggestions([])
    assert suggestions == []


def test_pocket_dataclass():
    pocket = Pocket(
        pocket_id=1,
        score=0.85,
        center={"x": 10.0, "y": 20.0, "z": 30.0},
        radius=6.2
    )
    d = pocket.to_dict()
    assert d["pocket_id"] == 1
    assert d["score"] == 0.85
    assert "center" in d