"""
tests/test_protonation.py
=========================
Basic tests for Phase 7 protonation pipeline.
"""

from docking_workflow.protonation import is_pdb2pqr_available, protonate_receptor


def test_protonate_graceful_when_pdb2pqr_missing():
    """Should not crash if PDB2PQR is not installed."""
    minimal_pdb = "ATOM      1  CA  ALA A   1      0.000   0.000   0.000  1.00  0.00           C"
    result = protonate_receptor(minimal_pdb, ph=7.4)
    # If tool missing, it returns original text
    assert "ATOM" in result


def test_availability_check():
    # Just ensure the function runs without error
    available = is_pdb2pqr_available()
    assert isinstance(available, bool)
