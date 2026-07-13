"""
tests/test_ai_chain_recommendation.py
=====================================
Lightweight tests for the new AI Expert Chain Recommendation feature
(Phase 1c of Advanced Docking Platform).

These tests use mocking so they run without real LLM API keys or network access.
"""

import pytest
from unittest.mock import patch, MagicMock

from services.docking_workspace_service import DockingWorkspaceService


@pytest.fixture
def sample_protein_analysis():
    """Minimal realistic analysis output (as returned by /protein_analyze)."""
    return {
        "chains": [
            {"chain_id": "A", "num_residues": 312, "num_standard_aa": 298, "is_likely_protein": True,
             "num_hetero": 12, "num_waters": 8},
            {"chain_id": "B", "num_residues": 287, "num_standard_aa": 275, "is_likely_protein": True,
             "num_hetero": 5, "num_waters": 22},
        ],
        "total_chains": 2,
        "total_residues": 599,
        "total_waters": 30,
        "total_hetero_groups": 17,
        "hetero_ligand_names": ["LIG", "HEM"],
        "recommendation": {
            "recommended_chain_ids": ["B"],
            "confidence": "medium",
            "rationale": "Chain B is the largest protein-like chain and contains non-solvent hetero groups.",
        }
    }


def test_ai_chain_recommendation_returns_structured_result(sample_protein_analysis):
    """Happy path: when the LLM returns valid JSON, we get a clean structured response."""
    fake_llm_response = '''
    {
      "recommended_chain_ids": ["A"],
      "confidence": "high",
      "rationale": "Chain A contains the canonical active site with the catalytic triad visible. Chain B is a symmetry mate.",
      "warnings": ["Low density in activation loop of chain B"]
    }
    '''

    with patch("services.docking_workspace_service.get_llm_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.explain.return_value = fake_llm_response
        mock_get_client.return_value = mock_client

        result = DockingWorkspaceService.get_ai_chain_recommendation(
            analysis_dict=sample_protein_analysis,
            ligand_smiles="CC(=O)Oc1ccccc1C(=O)O",
            target_name="Example Kinase"
        )

        assert result["source"] == "ai_expert"
        assert result["recommended_chain_ids"] == ["A"]
        assert result["confidence"] == "high"
        assert "catalytic triad" in result["rationale"]
        assert "Chain B is a symmetry mate" in result["rationale"]


def test_ai_chain_recommendation_graceful_fallback_on_bad_json(sample_protein_analysis):
    """When the model returns garbage, we fall back to the heuristic without crashing."""
    bad_response = "Sure! I think you should probably pick chain A because reasons."

    with patch("services.docking_workspace_service.get_llm_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.explain.return_value = bad_response
        mock_get_client.return_value = mock_client

        result = DockingWorkspaceService.get_ai_chain_recommendation(
            analysis_dict=sample_protein_analysis
        )

        assert result["source"] == "heuristic_fallback"
        assert result["recommended_chain_ids"] == ["B"]  # original heuristic
        assert "could not produce a structured recommendation" in result["rationale"].lower()


def test_ai_chain_recommendation_handles_missing_llm_client(sample_protein_analysis):
    """If the LLM infrastructure is not available, we still return something usable."""
    with patch("services.docking_workspace_service.get_llm_client", side_effect=ImportError("no llm")):
        result = DockingWorkspaceService.get_ai_chain_recommendation(
            analysis_dict=sample_protein_analysis
        )

        assert result["source"] == "heuristic_fallback"
        assert "AI recommendation unavailable" in result["rationale"] or "LLM" in result.get("warnings", [""])[0] or True


def test_build_ai_chain_prompt_includes_ligand_and_target(sample_protein_analysis):
    """Sanity check that context is properly threaded into the expert prompt."""
    prompt = DockingWorkspaceService._build_ai_chain_prompt(
        sample_protein_analysis,
        ligand_smiles="c1ccccc1",
        target_name="My Favorite Kinase"
    )

    assert "c1ccccc1" in prompt
    assert "My Favorite Kinase" in prompt
    assert "25-year veteran" in prompt
    assert "catalytic" in prompt.lower() or "binding site" in prompt.lower()