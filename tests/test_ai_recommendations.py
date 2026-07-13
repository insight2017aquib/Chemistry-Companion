"""
tests/test_ai_recommendations.py
==================================
Tests for the AI Recommendation Framework (Phase 01 Foundation).

Tests cover:
- Recommendation dataclass validation
- recommend_chain (wraps existing AI chain logic)
- recommend_pocket / recommend_waters / recommend_cofactors / recommend_metals (stubs)

All tests use mocking — no real API keys or network access required.
"""

import pytest
from unittest.mock import patch, MagicMock

from services.ai.models import Recommendation
from services.ai.recommendations import (
    recommend_chain,
    recommend_pocket,
    recommend_waters,
    recommend_cofactors,
    recommend_metals,
)


# ═══════════════════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_analysis():
    """Minimal protein analysis dict (as returned by analyze_protein)."""
    return {
        "chains": [
            {
                "chain_id": "A",
                "num_residues": 312,
                "num_standard_aa": 298,
                "is_likely_protein": True,
                "num_hetero": 12,
                "num_waters": 8,
            },
            {
                "chain_id": "B",
                "num_residues": 287,
                "num_standard_aa": 275,
                "is_likely_protein": True,
                "num_hetero": 5,
                "num_waters": 22,
            },
        ],
        "total_chains": 2,
        "total_residues": 599,
        "total_waters": 30,
        "total_hetero_groups": 17,
        "recommendation": {
            "recommended_chain_ids": ["A"],
            "confidence": "medium",
            "rationale": "Chain A is the largest protein-like chain.",
        },
    }


@pytest.fixture
def sample_pdb_text():
    """Minimal PDB text for stub functions."""
    return "ATOM      1  CA  ALA A   1       0.000   0.000   0.000  1.00  0.00           C\n"


# ═══════════════════════════════════════════════════════════════════════════
#  Recommendation Dataclass Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestRecommendationDataclass:
    def test_valid_recommendation(self):
        rec = Recommendation(
            recommendation=["A"],
            confidence="high",
            reasoning="Chain A has the binding site.",
        )
        assert rec.recommendation == ["A"]
        assert rec.confidence == "high"
        assert rec.reasoning == "Chain A has the binding site."
        assert rec.provider_used is None
        assert rec.metadata == {}

    def test_recommendation_with_metadata(self):
        rec = Recommendation(
            recommendation={"keep": True},
            confidence="medium",
            reasoning="test",
            provider_used="groq",
            metadata={"warnings": ["low resolution"]},
        )
        assert rec.provider_used == "groq"
        assert rec.metadata["warnings"] == ["low resolution"]

    def test_invalid_confidence_raises(self):
        with pytest.raises(ValueError, match="confidence must be one of"):
            Recommendation(
                recommendation=None,
                confidence="very_high",
                reasoning="test",
            )

    def test_none_metadata_becomes_empty_dict(self):
        rec = Recommendation(
            recommendation=None,
            confidence="low",
            reasoning="test",
            metadata=None,
        )
        assert rec.metadata == {}


# ═══════════════════════════════════════════════════════════════════════════
#  recommend_chain Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestRecommendChain:
    def test_recommend_chain_returns_recommendation(self, sample_analysis):
        """recommend_chain should always return a valid Recommendation."""
        fake_result = {
            "recommended_chain_ids": ["A"],
            "confidence": "high",
            "rationale": "Chain A contains the active site.",
            "source": "ai_expert",
            "warnings": [],
        }

        with patch(
            "services.docking_workspace_service.DockingWorkspaceService.get_ai_chain_recommendation",
            return_value=fake_result,
        ):
            rec = recommend_chain(sample_analysis, ligand_smiles="CCO")

            assert isinstance(rec, Recommendation)
            assert rec.recommendation == ["A"]
            assert rec.confidence == "high"
            assert "active site" in rec.reasoning
            assert rec.provider_used == "ai_expert"

    def test_recommend_chain_passes_context(self, sample_analysis):
        """Ligand SMILES and target name should be forwarded."""
        with patch(
            "services.docking_workspace_service.DockingWorkspaceService.get_ai_chain_recommendation",
            return_value={
                "recommended_chain_ids": ["B"],
                "confidence": "medium",
                "rationale": "test",
                "source": "ai_expert",
            },
        ) as mock_method:
            recommend_chain(
                sample_analysis,
                ligand_smiles="c1ccccc1",
                target_name="Test Kinase",
            )

            mock_method.assert_called_once_with(
                analysis_dict=sample_analysis,
                ligand_smiles="c1ccccc1",
                target_name="Test Kinase",
            )

    def test_recommend_chain_handles_exception(self, sample_analysis):
        """On unexpected errors, returns heuristic fallback."""
        with patch(
            "services.docking_workspace_service.DockingWorkspaceService.get_ai_chain_recommendation",
            side_effect=RuntimeError("LLM down"),
        ):
            rec = recommend_chain(sample_analysis)

            assert isinstance(rec, Recommendation)
            assert rec.confidence == "low"
            assert rec.recommendation == ["A"]  # from heuristic
            assert rec.provider_used is None
            assert "error" in rec.metadata

    def test_recommend_chain_heuristic_fallback_on_all_failure(self, sample_analysis):
        """When everything fails, returns the heuristic recommendation."""
        with patch(
            "services.docking_workspace_service.DockingWorkspaceService.get_ai_chain_recommendation",
            side_effect=Exception("unexpected"),
        ):
            rec = recommend_chain(sample_analysis)

            assert isinstance(rec, Recommendation)
            assert rec.confidence == "low"
            assert rec.recommendation == ["A"]
            assert "heuristic_fallback" in str(rec.metadata.get("source", ""))


# ═══════════════════════════════════════════════════════════════════════════
#  Stub Function Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestStubRecommendations:
    """All four stub functions should return valid Recommendation objects."""

    def test_recommend_pocket_returns_stub(self, sample_pdb_text):
        rec = recommend_pocket(sample_pdb_text)

        assert isinstance(rec, Recommendation)
        assert rec.recommendation is None
        assert rec.confidence == "low"
        assert "not yet implemented" in rec.reasoning.lower()
        assert rec.provider_used is None
        assert rec.metadata["status"] == "stub"

    def test_recommend_waters_returns_stub(self, sample_pdb_text):
        rec = recommend_waters(sample_pdb_text)

        assert isinstance(rec, Recommendation)
        assert rec.recommendation is None
        assert rec.confidence == "low"
        assert "not yet implemented" in rec.reasoning.lower()
        assert rec.metadata["phase"] == "02"

    def test_recommend_cofactors_returns_stub(self, sample_pdb_text):
        rec = recommend_cofactors(sample_pdb_text)

        assert isinstance(rec, Recommendation)
        assert rec.recommendation is None
        assert rec.confidence == "low"
        assert "not yet implemented" in rec.reasoning.lower()

    def test_recommend_metals_returns_stub(self, sample_pdb_text):
        rec = recommend_metals(sample_pdb_text)

        assert isinstance(rec, Recommendation)
        assert rec.recommendation is None
        assert rec.confidence == "low"
        assert "not yet implemented" in rec.reasoning.lower()

    def test_all_stubs_accept_analysis_dict(self, sample_pdb_text, sample_analysis):
        """Stub functions should accept an optional analysis_dict parameter."""
        for fn in (recommend_pocket, recommend_waters, recommend_cofactors, recommend_metals):
            rec = fn(sample_pdb_text, analysis_dict=sample_analysis)
            assert isinstance(rec, Recommendation)


# ═══════════════════════════════════════════════════════════════════════════
#  Import Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestImports:
    def test_import_from_package(self):
        """All public names should be importable from services.ai."""
        from services.ai import (
            AIProviderManager,
            AIResponse,
            HealthCheckResult,
            Recommendation,
            recommend_chain,
            recommend_pocket,
            recommend_waters,
            recommend_cofactors,
            recommend_metals,
        )

    def test_recommendation_module_exports(self):
        """Check __all__ exports."""
        from services.ai import recommendations
        assert hasattr(recommendations, "__all__")
        for name in recommendations.__all__:
            assert hasattr(recommendations, name)
