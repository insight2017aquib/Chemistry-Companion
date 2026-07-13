"""
services/ai/provider_manager.py
================================
Unified AI Provider Manager for Chemistry Companion.

This module provides a clean facade over the existing ``core/llm_utils.py``
multi-provider infrastructure, adding:

- **Gemini support** (registered in the provider registry)
- **Health checks** per provider
- **Structured JSON responses** with automatic parsing
- **Provider role semantics** (fast vs. reasoning)
- **Provider status dashboard** data

Architecture Note
-----------------
This module *delegates* to ``core/llm_utils.py`` for actual API calls,
retries, failover, and caching.  It does NOT duplicate that infrastructure.
See ADR-001 in ``docs/ARCHITECTURE_DECISIONS.md``.

Usage
-----
::

    from services.ai.provider_manager import AIProviderManager

    manager = AIProviderManager()

    # Simple query
    response = manager.query("Explain the molecule CCO")
    print(response.text, response.provider_used)

    # Structured JSON query
    result = manager.query_structured(
        "Return JSON with key 'answer'",
        expected_keys=["answer"],
    )
    print(result["answer"])

    # Health check
    health = manager.health_check("groq")
    print(health.available, health.latency_ms)
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

from services.ai.models import AIResponse, HealthCheckResult

# ---------------------------------------------------------------------------
# Environment & logger
# ---------------------------------------------------------------------------
load_dotenv()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Gemini registration — extend the existing provider registry
# ---------------------------------------------------------------------------

def _ensure_gemini_registered() -> None:
    """
    Register Gemini in the core provider registry if not already present.

    This is called once during module import.  It adds Gemini to the
    existing ``_PROVIDER_REGISTRY`` dict in ``core/llm_utils.py`` so that
    all existing infrastructure (failover, caching, etc.) works with
    Gemini automatically.
    """
    try:
        from core.llm_utils import _PROVIDER_REGISTRY

        if "gemini" not in _PROVIDER_REGISTRY:
            _PROVIDER_REGISTRY["gemini"] = {
                "env_key": "GEMINI_API_KEY",
                "default_model": "gemini-2.0-flash",
                "display_name": "Google Gemini (2.0 Flash)",
                "api_url": "https://generativelanguage.googleapis.com/v1beta",
                "note": "Google AI; free tier available. Uses REST API (no SDK).",
            }
            logger.info("Registered Gemini provider in core registry.")
    except ImportError:
        logger.warning("Could not import core.llm_utils to register Gemini.")


# Register on module import
_ensure_gemini_registered()


# ---------------------------------------------------------------------------
# Gemini-specific API adapter
# ---------------------------------------------------------------------------

def _call_gemini(api_key: str, model: str, prompt: str, timeout: int = 30) -> str:
    """
    Call the Gemini REST API directly.

    Gemini uses a different request/response format than OpenAI-compatible
    providers.  This adapter normalizes the interface.

    Parameters
    ----------
    api_key : str
        Gemini API key (passed as query parameter).
    model : str
        Model identifier (e.g. "gemini-2.0-flash").
    prompt : str
        User message content.
    timeout : int
        HTTP request timeout in seconds.

    Returns
    -------
    str
        The model's text response.

    Raises
    ------
    requests.exceptions.RequestException
        On HTTP or network failure.
    ValueError
        On malformed response.
    """
    url = (
        f"https://generativelanguage.googleapis.com/v1beta"
        f"/models/{model}:generateContent"
        f"?key={api_key}"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
    }

    headers = {"Content-Type": "application/json"}

    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()

    data = response.json()

    # Extract text from Gemini's response format
    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError("Gemini returned empty candidates array.")

    content = candidates[0].get("content", {})
    parts = content.get("parts", [])
    if not parts:
        raise ValueError("Gemini returned empty parts in first candidate.")

    text = parts[0].get("text", "")
    if not text:
        raise ValueError("Gemini returned empty text in first part.")

    return text


# ---------------------------------------------------------------------------
# AIProviderManager
# ---------------------------------------------------------------------------

class AIProviderManager:
    """
    Unified AI provider management with health checks, failover, and
    structured response support.

    Wraps ``core/llm_utils.py`` provider infrastructure and adds:

    - Gemini provider support
    - Health check per provider
    - Structured JSON response mode
    - Provider role semantics (fast vs. reasoning)
    - Provider status dashboard data

    Parameters
    ----------
    fast_provider : Optional[str]
        Default provider for fast/simple queries.
        Falls back to ``DEFAULT_FAST_PROVIDER`` env var, then ``"groq"``.
    reasoning_provider : Optional[str]
        Default provider for complex reasoning tasks.
        Falls back to ``DEFAULT_REASONING_PROVIDER`` env var, then ``"gemini"``.
    fallback_chain : Optional[List[str]]
        Ordered list of providers to try on failure.
        Falls back to ``FALLBACK_CHAIN`` env var, then config, then all
        available providers.
    """

    def __init__(
        self,
        fast_provider: Optional[str] = None,
        reasoning_provider: Optional[str] = None,
        fallback_chain: Optional[List[str]] = None,
    ) -> None:
        self._fast_provider = (
            fast_provider
            or os.getenv("DEFAULT_FAST_PROVIDER", "groq")
        ).strip().lower()

        self._reasoning_provider = (
            reasoning_provider
            or os.getenv("DEFAULT_REASONING_PROVIDER", "gemini")
        ).strip().lower()

        if fallback_chain is not None:
            self._fallback_chain = [p.strip().lower() for p in fallback_chain]
        else:
            env_chain = os.getenv("FALLBACK_CHAIN", "")
            if env_chain.strip():
                self._fallback_chain = [
                    p.strip().lower()
                    for p in env_chain.split(",")
                    if p.strip()
                ]
            else:
                self._fallback_chain = ["groq", "deepseek", "openrouter", "gemini"]

        # Track last provider used (for recommendation metadata)
        self._last_provider_used: Optional[str] = None

    # -- Properties ---------------------------------------------------------

    @property
    def fast_provider(self) -> str:
        """Return the configured fast provider name."""
        return self._fast_provider

    @property
    def reasoning_provider(self) -> str:
        """Return the configured reasoning provider name."""
        return self._reasoning_provider

    @property
    def last_provider_used(self) -> Optional[str]:
        """Return the provider that handled the last query."""
        return self._last_provider_used

    # -- Core Query ---------------------------------------------------------

    def query(
        self,
        prompt: str,
        provider: Optional[str] = None,
        timeout: int = 30,
    ) -> AIResponse:
        """
        Send a prompt to an AI provider with automatic failover.

        Parameters
        ----------
        prompt : str
            The prompt text.
        provider : Optional[str]
            Specific provider to use.  If None, uses the configured
            fast provider with fallback chain.
        timeout : int
            Request timeout in seconds.

        Returns
        -------
        AIResponse
            Always contains a usable response — never raises on
            provider failure (returns error in AIResponse instead).
        """
        # Build provider chain: requested provider first, then fallbacks
        chain = self._build_chain(provider)

        if not chain:
            self._last_provider_used = None
            return AIResponse(
                text="No AI providers configured. Please set at least one API key.",
                provider_used="none",
                error="No providers available",
            )

        primary_name = chain[0]["provider"]
        last_error = None

        for entry in chain:
            prov_name = entry["provider"]
            api_key = entry["api_key"]
            model = entry["model"]
            is_primary = (prov_name == primary_name)

            start_time = time.time()

            try:
                if prov_name == "gemini":
                    text = _call_gemini(api_key, model, prompt, timeout=timeout)
                else:
                    from core.llm_utils import _call_provider
                    text = _call_provider(prov_name, api_key, model, prompt, timeout=timeout)

                elapsed_ms = (time.time() - start_time) * 1000
                self._last_provider_used = prov_name

                logger.info(
                    "AI query succeeded: provider=%s, model=%s, latency=%.0fms%s",
                    prov_name, model, elapsed_ms,
                    "" if is_primary else " (fallback)",
                )

                return AIResponse(
                    text=text,
                    provider_used=prov_name,
                    model_used=model,
                    latency_ms=round(elapsed_ms, 1),
                    is_fallback=not is_primary,
                )

            except Exception as exc:
                elapsed_ms = (time.time() - start_time) * 1000
                last_error = f"[{prov_name}] {type(exc).__name__}: {exc}"
                logger.warning(
                    "AI query failed: provider=%s, latency=%.0fms, error=%s",
                    prov_name, elapsed_ms, last_error,
                )

        # All providers failed
        self._last_provider_used = None
        return AIResponse(
            text="All AI providers failed. Please check your API keys and network connectivity.",
            provider_used="none",
            error=last_error,
        )

    # -- Structured Query ---------------------------------------------------

    def query_structured(
        self,
        prompt: str,
        expected_keys: Optional[List[str]] = None,
        provider: Optional[str] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """
        Send a prompt expecting a JSON response and parse it.

        Parameters
        ----------
        prompt : str
            The prompt text.  Should instruct the model to return JSON.
        expected_keys : Optional[List[str]]
            Keys expected in the JSON response for validation.
        provider : Optional[str]
            Specific provider to use.
        timeout : int
            Request timeout in seconds.

        Returns
        -------
        Dict[str, Any]
            Parsed JSON response.  On failure, returns a dict with
            ``"error"`` key describing the issue.
        """
        response = self.query(prompt, provider=provider, timeout=timeout)

        if response.error and response.provider_used == "none":
            return {
                "error": response.error,
                "raw_text": response.text,
                "provider_used": response.provider_used,
            }

        # Parse JSON from the response
        parsed = self._extract_json(response.text)

        if parsed is None:
            return {
                "error": "Could not parse JSON from AI response",
                "raw_text": response.text,
                "provider_used": response.provider_used,
            }

        # Validate expected keys
        if expected_keys:
            missing = [k for k in expected_keys if k not in parsed]
            if missing:
                parsed["_missing_keys"] = missing
                parsed["_warning"] = f"Response missing expected keys: {missing}"

        parsed["_provider_used"] = response.provider_used
        parsed["_model_used"] = response.model_used
        parsed["_latency_ms"] = response.latency_ms

        return parsed

    # -- Health Checks ------------------------------------------------------

    def health_check(self, provider: Optional[str] = None) -> List[HealthCheckResult]:
        """
        Check health of one or all providers.

        Parameters
        ----------
        provider : Optional[str]
            If specified, check only this provider.
            If None, check all registered providers.

        Returns
        -------
        List[HealthCheckResult]
            Health status for each checked provider.
        """
        if provider:
            return [self._check_single_provider(provider)]

        results = []
        for prov_name in self._get_registered_providers():
            results.append(self._check_single_provider(prov_name))
        return results

    def _check_single_provider(self, provider: str) -> HealthCheckResult:
        """Run a lightweight health check against a single provider."""
        try:
            from core.llm_utils import _PROVIDER_REGISTRY
        except ImportError:
            return HealthCheckResult(
                provider=provider,
                available=False,
                error="core.llm_utils not importable",
            )

        info = _PROVIDER_REGISTRY.get(provider)
        if info is None:
            return HealthCheckResult(
                provider=provider,
                available=False,
                error=f"Unknown provider: {provider}",
            )

        api_key = os.getenv(info["env_key"], "")
        if not api_key:
            return HealthCheckResult(
                provider=provider,
                available=False,
                error=f"No API key configured ({info['env_key']})",
                model=info["default_model"],
                has_api_key=False,
            )

        # Send a minimal test prompt
        test_prompt = "Respond with exactly: OK"
        start_time = time.time()

        try:
            if provider == "gemini":
                _call_gemini(api_key, info["default_model"], test_prompt, timeout=10)
            else:
                from core.llm_utils import _call_provider
                _call_provider(provider, api_key, info["default_model"], test_prompt, timeout=10)

            elapsed_ms = (time.time() - start_time) * 1000

            return HealthCheckResult(
                provider=provider,
                available=True,
                latency_ms=round(elapsed_ms, 1),
                model=info["default_model"],
                has_api_key=True,
            )

        except Exception as exc:
            elapsed_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                provider=provider,
                available=False,
                latency_ms=round(elapsed_ms, 1),
                error=f"{type(exc).__name__}: {exc}",
                model=info["default_model"],
                has_api_key=True,
            )

    # -- Provider Status ----------------------------------------------------

    def get_provider_status(self) -> List[Dict[str, Any]]:
        """
        Return status information for all registered providers.

        Designed for dashboard display — does NOT make API calls.
        For live availability, use ``health_check()``.

        Returns
        -------
        List[Dict[str, Any]]
            One entry per provider with id, display_name, has_key, roles.
        """
        try:
            from core.llm_utils import _PROVIDER_REGISTRY
        except ImportError:
            return []

        results = []
        for prov_id, info in _PROVIDER_REGISTRY.items():
            has_key = bool(os.getenv(info["env_key"], ""))
            roles = []
            if prov_id == self._fast_provider:
                roles.append("fast")
            if prov_id == self._reasoning_provider:
                roles.append("reasoning")
            if prov_id in self._fallback_chain:
                roles.append("fallback")

            results.append({
                "id": prov_id,
                "display_name": info["display_name"],
                "has_api_key": has_key,
                "default_model": info["default_model"],
                "note": info["note"],
                "roles": roles,
                "env_key": info["env_key"],
            })

        return results

    def get_fast_provider(self) -> str:
        """Return the name of the fast provider."""
        return self._fast_provider

    def get_reasoning_provider(self) -> str:
        """Return the name of the reasoning provider."""
        return self._reasoning_provider

    # -- Internal Helpers ---------------------------------------------------

    def _build_chain(self, override_provider: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Build an ordered list of providers to try, with API keys.

        Delegates to the existing ``_resolve_provider_chain`` when possible,
        but handles the override and Gemini-specific logic.
        """
        chain: List[Dict[str, str]] = []
        seen: set = set()

        try:
            from core.llm_utils import _PROVIDER_REGISTRY
        except ImportError:
            return chain

        def _add(prov_name: str) -> None:
            if prov_name in seen:
                return
            info = _PROVIDER_REGISTRY.get(prov_name)
            if info is None:
                return
            api_key = os.getenv(info["env_key"], "")
            if not api_key:
                return
            seen.add(prov_name)
            chain.append({
                "provider": prov_name,
                "api_key": api_key,
                "model": info["default_model"],
            })

        # Priority 1: explicit override
        if override_provider:
            _add(override_provider.strip().lower())

        # Priority 2: fast provider (default primary)
        _add(self._fast_provider)

        # Priority 3: configured fallback chain
        for prov in self._fallback_chain:
            _add(prov)

        # Priority 4: any remaining registered providers with keys
        for prov_name in _PROVIDER_REGISTRY:
            _add(prov_name)

        return chain

    @staticmethod
    def _get_registered_providers() -> List[str]:
        """Return names of all registered providers."""
        try:
            from core.llm_utils import _PROVIDER_REGISTRY
            return list(_PROVIDER_REGISTRY.keys())
        except ImportError:
            return []

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from LLM response text.

        Handles common patterns:
        - Pure JSON
        - JSON wrapped in ```json ... ``` code fences
        - JSON embedded in surrounding text
        """
        if not text or not isinstance(text, str):
            return None

        text = text.strip()

        # Remove markdown code fences
        if text.startswith("```"):
            lines = text.split("```")
            if len(lines) >= 3:
                # Content between first and second ```
                text = lines[1]
                if text.lower().startswith("json"):
                    text = text[4:]
                text = text.strip()
            elif len(lines) == 2:
                text = lines[1]
                if text.lower().startswith("json"):
                    text = text[4:]
                text = text.strip()

        # Try direct parse
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            pass

        # Scan for the first *balanced* {...} object.
        #
        # A naive find("{")..rfind("}") breaks whenever the model appends
        # commentary that itself contains braces (e.g. "here is a more
        # conservative answer: {...}"), because the slice then spans two
        # objects and is invalid JSON. Balanced matching, skipping over string
        # literals and escapes, extracts the first complete object instead.
        for start in range(len(text)):
            if text[start] != "{":
                continue
            depth = 0
            in_string = False
            escaped = False
            for i in range(start, len(text)):
                ch = text[i]
                if in_string:
                    if escaped:
                        escaped = False
                    elif ch == "\\":
                        escaped = True
                    elif ch == '"':
                        in_string = False
                    continue
                if ch == '"':
                    in_string = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start:i + 1])
                        except (json.JSONDecodeError, TypeError):
                            break  # malformed; try the next '{'
            # unbalanced from this '{' — keep scanning

        return None
