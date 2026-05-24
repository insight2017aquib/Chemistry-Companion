"""
llm/__init__.py
===============
LLM Integration module for docking explanations.
All dependencies (OpenRouter API, services) are optional.
"""

import logging

logger = logging.getLogger(__name__)

# Pure data models — always safe to import
from .explanation_models import DockingExplanationRequest, DockingExplanationResponse, PoseExplanationRequest

# Check if LLM backend is configured
HAS_LLM = False
try:
    from services.llm_service import OpenRouterClient
    HAS_LLM = True
except Exception:
    logger.warning("LLM service unavailable (OpenRouterClient could not be imported).")

# Attempt to load the explainer functions; provide safe stubs on failure
try:
    from .docking_explainer import explain_docking_result, explain_single_pose
except Exception as e:
    logger.warning("LLM docking_explainer unavailable: %s", e)

    def explain_docking_result(*a, **kw):
        return "LLM explanation unavailable (missing dependencies)."

    def explain_single_pose(*a, **kw):
        return "LLM explanation unavailable (missing dependencies)."

__all__ = [
    "DockingExplanationRequest",
    "DockingExplanationResponse",
    "PoseExplanationRequest",
    "explain_docking_result",
    "explain_single_pose",
    "HAS_LLM",
]
