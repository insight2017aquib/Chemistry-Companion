"""
services/ai/models.py
=====================
Data models for the AI Provider Manager and Recommendation Framework.

All models are plain dataclasses with no external dependencies,
ensuring they can be imported safely regardless of which optional
packages are installed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AIResponse:
    """
    Structured result from an AI provider query.

    Attributes
    ----------
    text : str
        The raw text response from the provider.
    provider_used : str
        Which provider generated this response (e.g. "groq", "gemini").
    model_used : Optional[str]
        The specific model identifier used.
    latency_ms : Optional[float]
        Round-trip latency in milliseconds.
    is_fallback : bool
        True if a fallback provider was used instead of the primary.
    error : Optional[str]
        Error description if the primary provider failed.
    """

    text: str
    provider_used: str
    model_used: Optional[str] = None
    latency_ms: Optional[float] = None
    is_fallback: bool = False
    error: Optional[str] = None


@dataclass
class HealthCheckResult:
    """
    Result of a provider health check.

    Attributes
    ----------
    provider : str
        Provider identifier (e.g. "groq", "gemini").
    available : bool
        Whether the provider responded successfully.
    latency_ms : Optional[float]
        Response time in milliseconds (None if unavailable).
    error : Optional[str]
        Error message if the check failed.
    model : Optional[str]
        Model used for the health check.
    has_api_key : bool
        Whether an API key is configured for this provider.
    """

    provider: str
    available: bool
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    model: Optional[str] = None
    has_api_key: bool = False


@dataclass
class Recommendation:
    """
    Structured AI recommendation result.

    Used by all ``recommend_*`` functions in the recommendation framework.
    Every recommendation includes a confidence level and human-readable
    reasoning, regardless of whether an LLM was used or a fallback was
    triggered.

    Attributes
    ----------
    recommendation : Any
        The actual recommendation payload. Type varies by function:
        - recommend_chain: List[str] (chain IDs)
        - recommend_pocket: Dict with pocket info
        - recommend_waters: Dict with water handling advice
        - recommend_cofactors: Dict with cofactor decisions
        - recommend_metals: Dict with metal handling advice
    confidence : str
        Confidence level: "high", "medium", or "low".
    reasoning : str
        Human-readable explanation of the recommendation.
    provider_used : Optional[str]
        Which AI provider generated this (None for heuristic/stub).
    metadata : Optional[Dict[str, Any]]
        Additional context (warnings, raw response, timing, etc.).
    """

    recommendation: Any
    confidence: str
    reasoning: str
    provider_used: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        """Validate confidence level."""
        valid_levels = ("high", "medium", "low")
        if self.confidence not in valid_levels:
            raise ValueError(
                f"confidence must be one of {valid_levels}, got {self.confidence!r}"
            )
        if self.metadata is None:
            self.metadata = {}
