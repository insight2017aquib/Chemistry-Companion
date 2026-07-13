"""
tests/test_ai_expert_recommendations.py
=====================================
Tests for the new Phase 4 AI expert recommendations and assistant helper functions.
"""

import pytest
from unittest.mock import MagicMock, patch

from services.ai.recommendations import ask_expert, recommend_pocket, recommend_waters, recommend_cofactors, recommend_metals


@pytest.fixture
def sample_analysis():
    return {
        "chains": [
            {"chain_id": "A", "num_residues": 150, "is_likely_protein": True},
        ],
        "total_chains": 1,
        "total_residues": 150,
        "total_waters": 12,
        "cofactors": [{"resname": "ATP", "chain_id": "A", "resnum": 100}],
        "metals": [{"resname": "ZN", "chain_id": "A", "resnum": 250}],
    }


def test_ask_expert_returns_structured_answer(sample_analysis):
    with patch("services.ai.recommendations.AIProviderManager.query") as mock_query:
        mock_query.return_value = MagicMock(
            text="Chain A is preferred because it contains the active site.",
            provider_used="groq",
            model_used="gpt",
            latency_ms=150.0,
            error=None,
        )

        result = ask_expert(
            question="Why is chain A recommended?",
            pdb_text="ATOM...",
            analysis_dict=sample_analysis,
            domain="chain",
        )

        assert result.recommendation["answer"] == "Chain A is preferred because it contains the active site."
        assert result.confidence == "medium"
        assert "active site" in result.reasoning
        assert result.provider_used == "groq"


def test_recommend_pocket_uses_detected_pocket_and_ai_reasoning(sample_analysis):
    with patch("services.ai.recommendations.DockingWorkspaceService") as mock_service:
        mock_service.detect_pockets.return_value = {
            "suggestions": [{"pocket_id": 1, "label": "Top pocket", "score": 0.95}],
            "tool_used": "fpocket",
        }
        with patch("services.ai.recommendations.AIProviderManager.query") as mock_query:
            mock_query.return_value = MagicMock(
                text="Pocket 1 is the most druggable site because it sits in the active site region.",
                provider_used="gemini",
                model_used="gemini-2.0-flash",
                latency_ms=200.0,
                error=None,
            )

            result = recommend_pocket("ATOM...", sample_analysis)

            assert result.recommendation["top_pocket"]["pocket_id"] == 1
            assert result.confidence == "medium"
            assert "druggable" in result.reasoning
            assert result.provider_used == "gemini"


def test_recommend_waters_falls_back_when_ai_not_available(sample_analysis):
    with patch("services.ai.recommendations.AIProviderManager.query") as mock_query:
        mock_query.return_value = MagicMock(
            text="No AI providers configured.",
            provider_used="none",
            model_used=None,
            latency_ms=None,
            error="No providers available",
        )

        result = recommend_waters("ATOM...", sample_analysis)

        assert result.confidence == "low"
        assert "No AI provider is configured" in result.reasoning
        assert result.provider_used is None


def test_recommend_cofactors_and_metals_return_low_confidence_stubs(sample_analysis):
    with patch("services.ai.recommendations.AIProviderManager.query") as mock_query:
        mock_query.return_value = MagicMock(
            text="No AI providers configured.",
            provider_used="none",
            model_used=None,
            latency_ms=None,
            error="No providers available",
        )

        cofactor_result = recommend_cofactors("ATOM...", sample_analysis)
        metal_result = recommend_metals("ATOM...", sample_analysis)

        assert cofactor_result.confidence == "low"
        assert metal_result.confidence == "low"
        assert cofactor_result.recommendation["cofactors"] == sample_analysis["cofactors"]
        assert metal_result.recommendation["metals"] == sample_analysis["metals"]
