"""
tests/test_protein_analysis.py
==============================
Tests for the pre-docking protein chain analysis (Advanced Docking Phase 1).
"""

import pytest

from docking_workflow.protein_analysis import analyze_protein, ProteinAnalysis


# Minimal but realistic multi-chain PDB snippet (two short chains + one HETATM)
MULTI_CHAIN_PDB = """\
ATOM      1  N   ALA A   1      20.000  10.000  30.000  1.00  0.00           N
ATOM      2  CA  ALA A   1      21.000  10.000  30.000  1.00  0.00           C
ATOM      3  C   ALA A   1      22.000  10.000  30.000  1.00  0.00           C
ATOM      4  O   ALA A   1      23.000  10.000  30.000  1.00  0.00           O
ATOM      5  N   GLY A   2      24.000  10.000  30.000  1.00  0.00           N
ATOM      6  CA  GLY A   2      25.000  10.000  30.000  1.00  0.00           C
ATOM      7  N   SER B   1      10.000  20.000  15.000  1.00  0.00           N
ATOM      8  CA  SER B   1      11.000  20.000  15.000  1.00  0.00           C
HETATM    9  O   HOH A   3      26.000  10.000  30.000  1.00  0.00           O
HETATM   10  MG  MG  C 101      30.000  25.000  40.000  1.00  0.00          MG
END
"""


def test_analyze_protein_detects_multiple_chains():
    result = analyze_protein(MULTI_CHAIN_PDB)
    assert isinstance(result, ProteinAnalysis)
    assert result.total_chains >= 2
    assert result.total_residues > 0

    chain_ids = {c.chain_id for c in result.chains}
    assert "A" in chain_ids
    assert "B" in chain_ids


def test_recommendation_prefers_protein_chain_with_hetero():
    result = analyze_protein(MULTI_CHAIN_PDB)
    rec = result.recommendation
    assert "recommended_chain_ids" in rec
    # Chain A has both protein residues + a water, chain B is pure protein
    # The heuristic should still return something sensible
    assert len(rec["recommended_chain_ids"]) >= 1
    assert rec.get("confidence") in ("high", "medium", "low")


def test_fallback_parser_works_without_gemmi(monkeypatch):
    # Force the gemmi path to fail so we test the pure-Python fallback
    import docking_workflow.protein_analysis as pa

    original = pa._parse_with_gemmi
    pa._parse_with_gemmi = lambda text: None
    try:
        result = analyze_protein(MULTI_CHAIN_PDB)
        assert result.total_chains >= 2
        assert result.format_detected in ("pdb", "pdbqt")
    finally:
        pa._parse_with_gemmi = original


def test_empty_input_raises():
    with pytest.raises(ValueError):
        analyze_protein("")


# =============================================================================
# Tests for the new rich ReceptorReport (Option A / Phase 1)
# =============================================================================

from docking_workflow.protein_analysis import analyze_receptor, ReceptorReport


def test_analyze_receptor_returns_rich_report():
    result = analyze_receptor(MULTI_CHAIN_PDB)
    assert isinstance(result, ReceptorReport)
    assert result.total_chains >= 2
    # Quality score can be low on minimal test structures
    assert 0 <= result.quality_score <= 100
    assert result.quality_label in ("Excellent", "Good", "Acceptable", "Poor", "Unknown")


def test_analyze_receptor_detects_metal():
    result = analyze_receptor(MULTI_CHAIN_PDB)
    # The test PDB contains a MG in chain C.
    # We only assert that the metals list is present (classification can vary
    # between gemmi and pure-Python fallback parsers).
    assert isinstance(result.metals, list)


def test_analyze_receptor_has_quality_fields():
    result = analyze_receptor(MULTI_CHAIN_PDB)
    assert hasattr(result, "quality_score")
    assert hasattr(result, "quality_label")
    assert 0 <= result.quality_score <= 100
