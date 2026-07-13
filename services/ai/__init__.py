"""
services/ai/__init__.py
========================
AI Provider Manager and Recommendation Framework.

Phase 01 Foundation — provides unified AI provider access with:
- Multi-provider support (Groq, DeepSeek, OpenRouter, Gemini)
- Automatic failover and health checks
- Structured JSON response parsing
- Recommendation interfaces for protein preparation intelligence

Usage::

    from services.ai import AIProviderManager, recommend_chain

    # Direct provider access
    manager = AIProviderManager()
    response = manager.query("Explain this molecule: CCO")

    # Structured recommendations
    rec = recommend_chain(analysis_dict, ligand_smiles="CCO")
    print(rec.confidence, rec.reasoning)
"""

from services.ai.models import AIResponse, HealthCheckResult, Recommendation
from services.ai.provider_manager import AIProviderManager
from services.ai.recommendations import (
    ask_expert,
    recommend_chain,
    recommend_pocket,
    recommend_waters,
    recommend_cofactors,
    recommend_metals,
)

__all__ = [
    "AIProviderManager",
    "AIResponse",
    "HealthCheckResult",
    "Recommendation",
    "ask_expert",
    "recommend_chain",
    "recommend_pocket",
    "recommend_waters",
    "recommend_cofactors",
    "recommend_metals",
]
