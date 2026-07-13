"""
chemistry_companion/core/llm_utils.py

Multi-provider LLM explanation engine for Chemistry Companion.

Scientific / Engineering Note — Fallback Strategy
--------------------------------------------------
Cheminformatics explanations serve two audiences: researchers who need
methodological context and students who need intuitive summaries.  An LLM
provides the richest output, but *any* explanation is better than a crash
or an opaque error.  This module implements a **multi-layer degradation
strategy**:

    Layer 1 (Primary)   – Configurable LLM provider (Groq, DeepSeek,
                          OpenRouter).  Provides the most detailed,
                          context-aware explanation.
    Layer 2 (Fallback)  – Ordered list of alternative providers.  Each is
                          tried in sequence until one succeeds.
    Layer 3 (Template)  – Deterministic, template-based explanation that
                          requires *zero* API calls or credits.  It uses
                          domain-specific templates seeded with computed
                          molecular properties so the text is still useful.

Every call returns an ``LLMExplanation`` dataclass that records which
provider produced the text, whether a fallback was used, and any error
that occurred.  Callers never need to handle exceptions — the function
*always* returns a usable result.

Provider details
----------------
- **Groq** (default primary): Very fast inference, generous free tier
  (~30 req/min).  Uses ``llama-3.3-70b-versatile`` by default.
- **DeepSeek**: Pay-per-token via ``deepseek-chat``.  Watch for
  "Insufficient Balance" errors.
- **OpenRouter**: Aggregator supporting free models (e.g.
  ``deepseek/deepseek-v4-flash:free``).  May queue under load.

Switching providers
-------------------
At runtime (e.g. from a GUI dropdown)::

    from core.llm_utils import set_primary_provider, get_available_providers

    # Show dropdown options
    providers = get_available_providers()  # [{"id": "groq", ...}, ...]

    # User selects "deepseek"
    set_primary_provider("deepseek")

Via environment variables::

    CHEM_COMPANION_LLM__PRIMARY_PROVIDER=groq
    CHEM_COMPANION_LLM__FALLBACK_PROVIDERS=deepseek,openrouter

Features
--------
- Three providers: Groq, DeepSeek, OpenRouter
- Structured ``LLMExplanation`` result with ``provider_used`` metadata
- Configurable primary + ordered fallback chain
- Runtime provider switching for GUI integration
- In-memory LRU cache (keyed by explanation type + context hash)
- Automatic retry with back-off for transient errors
- Fine-grained error classification (balance, rate-limit, timeout, network)
- Clear logging via ``core.logging_utils``
- Thread-safe cache operations
- Complete type hints and docstrings

Usage
-----
::

    from core.llm_utils import generate_explanation

    result = generate_explanation(
        context={"smiles": "CCO", "descriptors": {...}},
        explanation_type="descriptor",
    )
    print(result.text)
    print(result.source)        # "groq" | "deepseek" | "openrouter" | "template" | "cached"
    print(result.provider_used) # "groq" | "deepseek" | "openrouter" | "template"
    print(result.is_fallback)

    # Override provider for a single call
    result = generate_explanation(context, provider="deepseek")
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

from core.logging_utils import get_logger

# ---------------------------------------------------------------------------
# Environment & logger
# ---------------------------------------------------------------------------
load_dotenv()
logger = get_logger("llm_utils")


# ═══════════════════════════════════════════════════════════════════════════
#  Provider Registry — static metadata for each supported LLM provider
# ═══════════════════════════════════════════════════════════════════════════

# Maps provider name → (env_var_for_api_key, default_model, display_name, api_url)
_PROVIDER_REGISTRY: Dict[str, Dict[str, str]] = {
    "groq": {
        "env_key": "GROQ_API_KEY",
        "default_model": "llama-3.3-70b-versatile",
        "display_name": "Groq (Llama 3.3 70B)",
        "api_url": "https://api.groq.com/openai/v1/chat/completions",
        "note": "Fast inference, free tier ~30 req/min.",
    },
    "deepseek": {
        "env_key": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
        "display_name": "DeepSeek",
        "api_url": "https://api.deepseek.com/v1/chat/completions",
        "note": "Pay-per-token; watch for Insufficient Balance.",
    },
    "openrouter": {
        "env_key": "OPENROUTER_API_KEY",
        "default_model": "deepseek/deepseek-v4-flash:free",
        "display_name": "OpenRouter (Free)",
        "api_url": "https://openrouter.ai/api/v1/chat/completions",
        "note": "Aggregator with free model tiers; may queue under load.",
    },
    "gemini": {
        "env_key": "GEMINI_API_KEY",
        "default_model": "gemini-2.0-flash",
        "display_name": "Google Gemini (2.0 Flash)",
        "api_url": "https://generativelanguage.googleapis.com/v1beta",
        "note": "Google AI; free tier available. Non-OpenAI format — use AIProviderManager.",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  Data Structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class LLMExplanation:
    """
    Structured result of an explanation request.

    Attributes
    ----------
    text : str
        The explanation text (always populated — never empty).
    source : str
        Origin of the explanation.  One of ``"groq"``, ``"deepseek"``,
        ``"openrouter"``, ``"template"``, or ``"cached"``.
    provider_used : str
        The provider that actually generated this explanation (same as
        ``source`` for LLM calls, ``"template"`` for fallback, or the
        *original* provider when served from cache).
    is_fallback : bool
        ``True`` when the primary provider was *not* used (i.e. a
        fallback provider or template produced the text).
    model_used : Optional[str]
        Model identifier when an LLM was used; ``None`` for templates.
    error : Optional[str]
        Human-readable error description if the primary provider failed.
    """

    text: str
    source: str
    provider_used: str
    is_fallback: bool
    model_used: Optional[str] = None
    error: Optional[str] = None


@unique
class LLMErrorKind(Enum):
    """Classified categories of LLM API errors."""

    INSUFFICIENT_BALANCE = "insufficient_balance"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    NETWORK = "network"
    AUTH = "authentication"
    INVALID_RESPONSE = "invalid_response"
    UNKNOWN = "unknown"


# ═══════════════════════════════════════════════════════════════════════════
#  In-memory LRU Cache
# ═══════════════════════════════════════════════════════════════════════════

class _ExplanationCache:
    """
    Thread-safe, bounded LRU cache for ``LLMExplanation`` objects.

    The cache key is a deterministic hash of ``(explanation_type, context)``.
    """

    def __init__(self, maxsize: int = 128) -> None:
        self._maxsize = max(1, maxsize)
        self._store: OrderedDict[str, LLMExplanation] = OrderedDict()
        self._lock = threading.Lock()

    # -- key helpers --------------------------------------------------------

    @staticmethod
    def _make_key(context: Dict[str, Any], explanation_type: str) -> str:
        """Create a deterministic cache key from *context* and *type*."""
        raw = json.dumps(
            {"type": explanation_type, "ctx": context},
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # -- public API ---------------------------------------------------------

    def get(
        self, context: Dict[str, Any], explanation_type: str
    ) -> Optional[LLMExplanation]:
        """Return cached explanation or ``None``."""
        key = self._make_key(context, explanation_type)
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
                hit = self._store[key]
                logger.debug("Cache HIT for key=%s...", key[:12])
                return LLMExplanation(
                    text=hit.text,
                    source="cached",
                    provider_used=hit.provider_used,
                    is_fallback=hit.is_fallback,
                    model_used=hit.model_used,
                    error=hit.error,
                )
        return None

    def put(
        self,
        context: Dict[str, Any],
        explanation_type: str,
        explanation: LLMExplanation,
    ) -> None:
        """Store an explanation in the cache, evicting the oldest if full."""
        key = self._make_key(context, explanation_type)
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = explanation
            while len(self._store) > self._maxsize:
                evicted_key, _ = self._store.popitem(last=False)
                logger.debug("Cache EVICT key=%s...", evicted_key[:12])

    def clear(self) -> None:
        """Remove all cached entries."""
        with self._lock:
            self._store.clear()
        logger.debug("Explanation cache cleared.")

    @property
    def size(self) -> int:
        """Current number of cached entries."""
        with self._lock:
            return len(self._store)


# Module-level singleton
_cache = _ExplanationCache(maxsize=128)


# ═══════════════════════════════════════════════════════════════════════════
#  Runtime Provider Override
# ═══════════════════════════════════════════════════════════════════════════

# Thread-safe mutable override — ``None`` means "use config default".
_runtime_primary_override: Optional[str] = None
_runtime_lock = threading.Lock()


def set_primary_provider(provider: str) -> None:
    """
    Override the primary LLM provider at runtime.

    This is designed for GUI dropdown integration.  The override persists
    for the lifetime of the process (or until ``reset_primary_provider``
    is called).  It takes precedence over ``LLMSettings.primary_provider``
    but does *not* mutate the config object.

    Parameters
    ----------
    provider : str
        One of ``"groq"``, ``"deepseek"``, ``"openrouter"``.

    Raises
    ------
    ValueError
        If the provider name is not in the registry.
    """
    global _runtime_primary_override
    provider = provider.strip().lower()
    if provider not in _PROVIDER_REGISTRY:
        supported = ", ".join(sorted(_PROVIDER_REGISTRY))
        raise ValueError(
            f"Unknown provider {provider!r}. Supported: {supported}"
        )
    with _runtime_lock:
        _runtime_primary_override = provider
    logger.info("Runtime primary provider set to: %s", provider)


def reset_primary_provider() -> None:
    """Remove the runtime provider override (revert to config default)."""
    global _runtime_primary_override
    with _runtime_lock:
        _runtime_primary_override = None
    logger.info("Runtime primary provider reset to config default.")


def _get_runtime_primary() -> Optional[str]:
    """Return the runtime override or ``None``."""
    with _runtime_lock:
        return _runtime_primary_override


# ═══════════════════════════════════════════════════════════════════════════
#  Error Classification
# ═══════════════════════════════════════════════════════════════════════════

def _classify_error(
    exc: Exception,
    response: Optional[requests.Response] = None,
) -> Tuple[LLMErrorKind, str]:
    """
    Classify an LLM API error into a structured ``LLMErrorKind``.

    Returns
    -------
    (kind, detail)
        A tuple of the error category and a human-readable message.
    """
    detail = str(exc)

    # Try to extract API error body
    if response is not None:
        try:
            body = response.json()
            if "error" in body:
                err_obj = body["error"]
                msg = err_obj.get("message", "") if isinstance(err_obj, dict) else str(err_obj)
                detail = msg or detail
        except (ValueError, TypeError, KeyError):
            pass

    detail_lower = detail.lower()

    if isinstance(exc, requests.exceptions.Timeout):
        return LLMErrorKind.TIMEOUT, detail

    if isinstance(exc, requests.exceptions.ConnectionError):
        return LLMErrorKind.NETWORK, detail

    # HTTP status-based classification
    if response is not None:
        status = response.status_code
        if status == 401:
            return LLMErrorKind.AUTH, detail
        if status == 429:
            return LLMErrorKind.RATE_LIMIT, detail
        if status == 402 or "insufficient" in detail_lower or "balance" in detail_lower:
            return LLMErrorKind.INSUFFICIENT_BALANCE, detail

    # String-based heuristics for non-HTTP errors
    if any(kw in detail_lower for kw in ("balance", "insufficient", "quota", "credits")):
        return LLMErrorKind.INSUFFICIENT_BALANCE, detail
    if any(kw in detail_lower for kw in ("rate", "limit", "throttl")):
        return LLMErrorKind.RATE_LIMIT, detail
    if "timeout" in detail_lower:
        return LLMErrorKind.TIMEOUT, detail
    if any(kw in detail_lower for kw in ("connect", "network", "dns", "resolve")):
        return LLMErrorKind.NETWORK, detail

    return LLMErrorKind.UNKNOWN, detail


# ═══════════════════════════════════════════════════════════════════════════
#  LLM Provider Calls
# ═══════════════════════════════════════════════════════════════════════════

def _build_prompt(context: Dict[str, Any], explanation_type: str) -> str:
    """
    Build a structured prompt string for the LLM from *context* and *type*.

    The prompt is tailored to each ``explanation_type`` so that the model
    receives relevant domain cues.
    """
    smiles = context.get("smiles", "N/A")

    if explanation_type == "descriptor":
        descriptors = context.get("descriptors", {})
        desc_block = "\n".join(f"  - {k}: {v}" for k, v in descriptors.items()) or "  (none provided)"
        return (
            "You are an expert computational chemist.  Given the following molecule "
            "and its computed molecular descriptors, provide a concise professional "
            "summary that a medicinal chemist would find useful.\n\n"
            f"SMILES: {smiles}\n\n"
            f"Descriptors:\n{desc_block}\n\n"
            "Cover key drug-likeness indicators, notable physicochemical properties, "
            "and any red flags.  Be precise and cite descriptor values."
        )

    if explanation_type == "docking":
        poses = context.get("poses", [])
        interactions = context.get("interactions", [])
        return (
            "You are an expert medicinal chemist.  Analyze the following molecular "
            "docking results.\n\n"
            f"Ligand SMILES: {smiles}\n\n"
            f"Top Poses:\n{json.dumps(poses[:5], indent=2, default=str)}\n\n"
            f"Key Interactions:\n{json.dumps(interactions, indent=2, default=str)}\n\n"
            "Provide a concise but professional summary of the binding affinity, "
            "the significance of the interactions, and the overall viability of "
            "this ligand."
        )

    if explanation_type == "spectra":
        spectra_data = context.get("spectra", {})
        return (
            "You are an expert in molecular spectroscopy.  Based on the following "
            "spectroscopic data and molecular structure, provide a clear "
            "interpretation.\n\n"
            f"SMILES: {smiles}\n\n"
            f"Spectra Data:\n{json.dumps(spectra_data, indent=2, default=str)}\n\n"
            "Identify key peaks/signals, correlate them with structural features, "
            "and provide a cohesive interpretation."
        )

    # General / unknown type
    extra = {k: v for k, v in context.items() if k != "smiles"}
    extra_block = json.dumps(extra, indent=2, default=str) if extra else "(none)"
    return (
        "You are an expert chemist.  Provide a clear, professional explanation "
        "for the following chemical analysis.\n\n"
        f"SMILES: {smiles}\n\n"
        f"Additional Context:\n{extra_block}\n\n"
        "Be precise, cite specific values, and keep the explanation concise."
    )


def _call_provider(
    provider: str,
    api_key: str,
    model: str,
    prompt: str,
    timeout: int = 30,
) -> str:
    """
    Make a single chat-completion call to the given provider.

    Parameters
    ----------
    provider : str
        ``"groq"``, ``"deepseek"``, or ``"openrouter"``.
    api_key : str
        Bearer token.
    model : str
        Model identifier.
    prompt : str
        User-role message content.
    timeout : int
        HTTP request timeout in seconds.

    Returns
    -------
    str
        The assistant's reply content.

    Raises
    ------
    requests.exceptions.RequestException
        On any HTTP or network failure.
    ValueError
        On malformed API response or unsupported provider.
    """
    if provider not in _PROVIDER_REGISTRY:
        raise ValueError(f"Unsupported LLM provider: {provider!r}")

    registry = _PROVIDER_REGISTRY[provider]

    # Resolve URL (DeepSeek allows env override for the base URL)
    if provider == "deepseek":
        base_url = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
        url = f"{base_url.rstrip('/')}/chat/completions"
    else:
        url = registry["api_url"]

    # Build headers — OpenRouter requires extra fields for ranking
    headers: Dict[str, str] = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if provider == "openrouter":
        headers["HTTP-Referer"] = "http://localhost:8000"
        headers["X-Title"] = "Chemistry Companion"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }

    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()

    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        raise ValueError("LLM returned empty choices array.")
    content = choices[0].get("message", {}).get("content", "")
    if not content:
        raise ValueError("LLM returned empty content in first choice.")
    return content


def _try_provider_with_retries(
    provider: str,
    api_key: str,
    model: str,
    prompt: str,
    max_retries: int = 2,
    timeout: int = 30,
) -> Tuple[Optional[str], Optional[LLMErrorKind], Optional[str]]:
    """
    Attempt an LLM call with exponential back-off for retryable errors.

    Returns
    -------
    (text, error_kind, error_detail)
        ``text`` is the response on success; on failure it is ``None`` and
        ``error_kind`` / ``error_detail`` describe what went wrong.
    """
    retryable = {LLMErrorKind.RATE_LIMIT, LLMErrorKind.TIMEOUT, LLMErrorKind.NETWORK}
    last_kind: Optional[LLMErrorKind] = None
    last_detail: Optional[str] = None

    for attempt in range(1, max_retries + 1):
        response: Optional[requests.Response] = None
        try:
            text = _call_provider(provider, api_key, model, prompt, timeout=timeout)
            return text, None, None
        except requests.exceptions.RequestException as exc:
            response = getattr(exc, "response", None)
            last_kind, last_detail = _classify_error(exc, response)
        except Exception as exc:
            last_kind, last_detail = _classify_error(exc)

        logger.warning(
            "Provider %s attempt %d/%d failed (%s): %s",
            provider, attempt, max_retries, last_kind.value if last_kind else "unknown", last_detail,
        )

        # Only retry on transient errors
        if last_kind not in retryable:
            break
        if attempt < max_retries:
            backoff = min(2 ** attempt, 8)
            logger.debug("Backing off %ds before retry...", backoff)
            time.sleep(backoff)

    return None, last_kind, last_detail


# ═══════════════════════════════════════════════════════════════════════════
#  Template-Based Fallback (Layer 3)
# ═══════════════════════════════════════════════════════════════════════════

# Registry of deterministic templates keyed by explanation_type.
_TEMPLATES: Dict[str, Callable[[Dict[str, Any]], str]] = {}


def _register_template(explanation_type: str):
    """Decorator to register a template function for a given type."""
    def decorator(fn: Callable[[Dict[str, Any]], str]):
        _TEMPLATES[explanation_type] = fn
        return fn
    return decorator


@_register_template("general")
def _template_general(context: Dict[str, Any]) -> str:
    smiles = context.get("smiles", "N/A")
    lines = [
        f"## Analysis Summary for {smiles}",
        "",
        "This is a template-based explanation generated without an LLM.",
    ]

    if "descriptors" in context:
        desc = context["descriptors"]
        lines.append("")
        lines.append("### Computed Descriptors")
        for key, value in desc.items():
            lines.append(f"- **{key}**: {value}")

    if "functional_groups" in context:
        groups = context["functional_groups"]
        if groups:
            lines.append("")
            lines.append("### Functional Groups Detected")
            for group, count in groups.items():
                lines.append(f"- {group}: {count}")

    lines += [
        "",
        "---",
        "*Note: This explanation was generated from templates because the "
        "LLM service was unavailable.  For richer, context-aware analysis, "
        "ensure a valid API key is configured.*",
    ]
    return "\n".join(lines)


@_register_template("descriptor")
def _template_descriptor(context: Dict[str, Any]) -> str:
    smiles = context.get("smiles", "N/A")
    desc = context.get("descriptors", {})

    lines = [
        f"## Descriptor Analysis for {smiles}",
        "",
    ]

    mw = desc.get("molecular_weight") or desc.get("mol_weight")
    logp = desc.get("logp") or desc.get("LogP")
    tpsa = desc.get("tpsa") or desc.get("TPSA")
    hbd = desc.get("hbd") or desc.get("HBD")
    hba = desc.get("hba") or desc.get("HBA")
    rot = desc.get("rotatable_bonds")

    if mw is not None:
        lines.append(f"- **Molecular Weight**: {mw:.2f} Da")
        if mw <= 500:
            lines.append("  - Within Lipinski MW threshold (<=500 Da)")
        else:
            lines.append("  - Exceeds Lipinski MW threshold (>500 Da) -- WARNING")
    if logp is not None:
        lines.append(f"- **LogP**: {logp:.2f}")
        if logp <= 5:
            lines.append("  - Acceptable lipophilicity (<=5)")
        else:
            lines.append("  - High lipophilicity (>5) -- WARNING")
    if tpsa is not None:
        lines.append(f"- **TPSA**: {tpsa:.1f} A^2")
        if tpsa <= 140:
            lines.append("  - Suggests reasonable oral bioavailability")
        else:
            lines.append("  - High TPSA may limit membrane permeability -- WARNING")
    if hbd is not None:
        lines.append(f"- **H-Bond Donors**: {hbd}")
    if hba is not None:
        lines.append(f"- **H-Bond Acceptors**: {hba}")
    if rot is not None:
        lines.append(f"- **Rotatable Bonds**: {rot}")
        if rot <= 10:
            lines.append("  - Good conformational rigidity")
        else:
            lines.append("  - High flexibility may reduce binding affinity -- WARNING")

    # Lipinski Rule of Five summary
    violations = 0
    if mw is not None and mw > 500:
        violations += 1
    if logp is not None and logp > 5:
        violations += 1
    if hbd is not None and hbd > 5:
        violations += 1
    if hba is not None and hba > 10:
        violations += 1

    lines.append("")
    lines.append(f"### Lipinski's Rule of Five: {violations} violation(s)")
    if violations == 0:
        lines.append("The compound satisfies all four Lipinski criteria, "
                      "suggesting reasonable oral drug-likeness.")
    elif violations == 1:
        lines.append("One violation is present.  Many successful drugs have "
                      "a single Ro5 violation -- further evaluation is warranted.")
    else:
        lines.append(f"With {violations} violations, oral bioavailability may "
                      "be limited.  Consider structural optimization.")

    lines += [
        "",
        "---",
        "*Template-based analysis -- LLM unavailable.  Configure a valid API "
        "key for richer explanations.*",
    ]
    return "\n".join(lines)


@_register_template("docking")
def _template_docking(context: Dict[str, Any]) -> str:
    smiles = context.get("smiles", "N/A")
    poses = context.get("poses", [])
    interactions = context.get("interactions", [])

    lines = [
        f"## Docking Results Summary for {smiles}",
        "",
    ]

    if poses:
        lines.append(f"**{len(poses)} pose(s)** were evaluated.")
        lines.append("")
        lines.append("| Rank | Affinity (kcal/mol) |")
        lines.append("|------|---------------------|")
        for i, pose in enumerate(poses[:5], 1):
            affinity = pose.get("affinity", "N/A")
            rank = pose.get("rank", i)
            lines.append(f"| {rank} | {affinity} |")

        best = min(poses[:5], key=lambda p: p.get("affinity", 0))
        best_aff = best.get("affinity", "N/A")
        lines.append("")
        lines.append(f"**Best affinity**: {best_aff} kcal/mol")
        if isinstance(best_aff, (int, float)):
            if best_aff <= -8.0:
                lines.append("This suggests **strong** binding potential.")
            elif best_aff <= -6.0:
                lines.append("This suggests **moderate** binding potential.")
            else:
                lines.append("Binding affinity is relatively weak; "
                             "structural optimization may be needed.")
    else:
        lines.append("No docking poses were provided.")

    if interactions:
        lines.append("")
        lines.append("### Key Interactions")
        lines.append("")
        lines.append("| Type | Residue | Distance (A) |")
        lines.append("|------|---------|--------------|")
        for ix in interactions[:10]:
            itype = ix.get("type", "Unknown")
            residue = ix.get("protein_residue", "?")
            dist = ix.get("distance", "?")
            lines.append(f"| {itype} | {residue} | {dist} |")

        # Interaction type summary
        hbonds = sum(1 for ix in interactions if "bond" in ix.get("type", "").lower())
        hydrophobic = sum(1 for ix in interactions if "hydrophobic" in ix.get("type", "").lower())
        if hbonds:
            lines.append(f"\n**{hbonds} hydrogen bond(s)** detected -- "
                         "important for binding specificity.")
        if hydrophobic:
            lines.append(f"**{hydrophobic} hydrophobic contact(s)** -- "
                         "contribute to binding stability.")

    lines += [
        "",
        "---",
        "*Template-based analysis -- LLM unavailable.  Configure a valid API "
        "key for richer docking interpretations.*",
    ]
    return "\n".join(lines)


@_register_template("spectra")
def _template_spectra(context: Dict[str, Any]) -> str:
    smiles = context.get("smiles", "N/A")
    spectra = context.get("spectra", {})

    lines = [
        f"## Spectral Data Summary for {smiles}",
        "",
    ]

    for domain, data in spectra.items():
        lines.append(f"### {domain}")
        if isinstance(data, dict):
            for k, v in data.items():
                lines.append(f"- {k}: {v}")
        elif isinstance(data, list):
            for item in data[:10]:
                lines.append(f"- {item}")
        else:
            lines.append(str(data))
        lines.append("")

    if not spectra:
        lines.append("No spectral data was provided for analysis.")

    lines += [
        "---",
        "*Template-based analysis -- LLM unavailable.  Configure a valid API "
        "key for richer spectral interpretations.*",
    ]
    return "\n".join(lines)


def _generate_template_explanation(
    context: Dict[str, Any],
    explanation_type: str,
) -> str:
    """
    Generate a deterministic, template-based explanation.

    Falls back to the ``"general"`` template if no type-specific template
    is registered.
    """
    template_fn = _TEMPLATES.get(explanation_type, _TEMPLATES.get("general"))
    if template_fn is None:
        # Absolute last resort — should never happen if general is registered
        return (
            f"Analysis for {context.get('smiles', 'unknown molecule')}.  "
            "No detailed template available for this explanation type.  "
            "Configure an LLM API key for richer explanations."
        )
    return template_fn(context)


# ═══════════════════════════════════════════════════════════════════════════
#  Provider Chain Resolution
# ═══════════════════════════════════════════════════════════════════════════

def _resolve_provider_chain(
    override_provider: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Build an ordered list of providers to try, with their API keys.

    Resolution priority:
    1. ``override_provider`` (from a single ``generate_explanation`` call)
    2. Runtime override set via ``set_primary_provider`` (GUI)
    3. ``LLMSettings.primary_provider`` from config
    4. Environment variable ``LLM_PROVIDER``

    The fallback list is appended after the primary, excluding duplicates.
    Each entry is ``{"provider": ..., "api_key": ..., "model": ...}``.
    Providers without API keys are silently skipped.
    """
    chain: List[Dict[str, str]] = []
    seen: set[str] = set()

    # --- Determine primary provider ---
    primary: Optional[str] = None
    fallback_list: List[str] = []

    # Priority 1: explicit override for this call
    if override_provider and override_provider.strip():
        primary = override_provider.strip().lower()

    # Priority 2: runtime override (GUI dropdown)
    if primary is None:
        primary = _get_runtime_primary()

    # Priority 3 & 4: config / env
    if primary is None:
        try:
            from core.config import get_settings
            settings = get_settings()
            llm_cfg = getattr(settings, "llm", None)
            if llm_cfg is not None:
                primary = getattr(llm_cfg, "primary_provider", None)
                fallback_list = list(getattr(llm_cfg, "fallback_providers", []))
        except Exception:
            pass

    if primary is None:
        primary = os.getenv("LLM_PROVIDER", "groq").strip().lower()

    # --- Build the chain: primary first, then fallbacks ---
    def _append_if_available(provider_name: str) -> None:
        """Add provider to chain if it has a valid API key."""
        if provider_name in seen:
            return
        info = _PROVIDER_REGISTRY.get(provider_name)
        if info is None:
            logger.debug("Skipping unknown provider %r", provider_name)
            return
        api_key = os.getenv(info["env_key"], "")
        if not api_key:
            logger.debug("Skipping provider %s (no API key in env %s)", provider_name, info["env_key"])
            return
        seen.add(provider_name)
        chain.append({
            "provider": provider_name,
            "api_key": api_key,
            "model": info["default_model"],
        })

    # Primary
    if primary:
        _append_if_available(primary)

    # Configured fallbacks
    for fb in fallback_list:
        fb_clean = fb.strip().lower()
        if fb_clean:
            _append_if_available(fb_clean)

    # Auto-discovery: add any remaining providers that have keys
    for prov_name in _PROVIDER_REGISTRY:
        _append_if_available(prov_name)

    return chain


def _get_llm_settings_field(field_name: str, default: Any = None) -> Any:
    """Safely read a field from ``LLMSettings`` in the config, with fallback."""
    try:
        from core.config import get_settings
        settings = get_settings()
        llm_cfg = getattr(settings, "llm", None)
        if llm_cfg is not None:
            return getattr(llm_cfg, field_name, default)
    except Exception:
        pass
    return default


# ═══════════════════════════════════════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════════════════════════════════════

def generate_explanation(
    context: Dict[str, Any],
    explanation_type: str = "general",
    provider: Optional[str] = None,
    force_fallback: bool = False,
) -> LLMExplanation:
    """
    Generate an explanation for a chemical analysis result.

    This is the **primary entry-point** for all LLM-powered explanations
    in Chemistry Companion.  It implements a multi-layer degradation
    strategy:

        1. Primary LLM provider (configurable, default: Groq)
        2. Fallback providers in configured order
        3. Deterministic template (zero API calls)

    Parameters
    ----------
    context : Dict[str, Any]
        Domain data for the explanation.  Expected keys vary by
        ``explanation_type``:

        - ``"general"``    -- ``smiles``, plus any extras
        - ``"descriptor"`` -- ``smiles``, ``descriptors`` dict
        - ``"docking"``    -- ``smiles``, ``poses`` list, ``interactions`` list
        - ``"spectra"``    -- ``smiles``, ``spectra`` dict
    explanation_type : str
        Category of explanation (default ``"general"``).
    provider : Optional[str]
        Override the primary provider for this single call only.
        E.g. ``provider="deepseek"`` to force DeepSeek regardless of config.
    force_fallback : bool
        If ``True``, skip all LLM calls and return the template immediately.
        Useful for testing or when credits are known to be exhausted.

    Returns
    -------
    LLMExplanation
        Always contains a usable ``text`` field -- this function never raises.

    Examples
    --------
    >>> result = generate_explanation({"smiles": "CCO"}, "general")
    >>> print(result.source)
    'groq'

    >>> result = generate_explanation({"smiles": "CCO"}, provider="deepseek")
    >>> print(result.provider_used)
    'deepseek'

    >>> result = generate_explanation({"smiles": "CCO"}, force_fallback=True)
    >>> print(result.source)
    'template'
    """
    # -- Guard: LLM globally disabled? ------------------------------------
    enable_llm = _get_llm_settings_field("enable_llm", default=True)
    if not enable_llm:
        logger.info("LLM is disabled via configuration; using template fallback.")
        force_fallback = True

    # -- Guard: force fallback ---------------------------------------------
    if force_fallback:
        text = _generate_template_explanation(context, explanation_type)
        return LLMExplanation(
            text=text,
            source="template",
            provider_used="template",
            is_fallback=True,
            error="Fallback forced (force_fallback=True or LLM disabled).",
        )

    # -- Check cache -------------------------------------------------------
    cache_enabled = _get_llm_settings_field("cache_enabled", default=True)
    if cache_enabled:
        cached = _cache.get(context, explanation_type)
        if cached is not None:
            return cached

    # -- Resolve provider chain --------------------------------------------
    chain = _resolve_provider_chain(override_provider=provider)
    max_retries = _get_llm_settings_field("max_retries", default=2)

    if not chain:
        logger.warning(
            "No LLM providers configured (missing API keys).  "
            "Falling back to template."
        )
        text = _generate_template_explanation(context, explanation_type)
        return LLMExplanation(
            text=text,
            source="template",
            provider_used="template",
            is_fallback=True,
            error="No LLM API keys configured.",
        )

    # -- Build prompt ------------------------------------------------------
    prompt = _build_prompt(context, explanation_type)

    # -- Try each provider in chain ----------------------------------------
    # The first provider in the chain is the "primary".  Any subsequent
    # provider that succeeds sets is_fallback=True.
    last_error_detail: Optional[str] = None
    primary_name = chain[0]["provider"]

    for prov in chain:
        provider_name = prov["provider"]
        api_key = prov["api_key"]
        model = prov["model"]
        is_primary = (provider_name == primary_name)

        logger.info(
            "Attempting LLM call: provider=%s, model=%s%s",
            provider_name, model, "" if is_primary else " (fallback)",
        )

        text, err_kind, err_detail = _try_provider_with_retries(
            provider=provider_name,
            api_key=api_key,
            model=model,
            prompt=prompt,
            max_retries=max_retries,
        )

        if text is not None:
            explanation = LLMExplanation(
                text=text,
                source=provider_name,
                provider_used=provider_name,
                is_fallback=not is_primary,
                model_used=model,
            )
            if cache_enabled:
                _cache.put(context, explanation_type, explanation)
            logger.info(
                "Explanation generated via %s (model=%s, fallback=%s).",
                provider_name, model, not is_primary,
            )
            return explanation

        # Log failure and try next provider
        last_error_detail = (
            f"[{provider_name}] "
            f"{err_kind.value if err_kind else 'unknown'}: {err_detail}"
        )
        logger.warning("Provider %s failed: %s", provider_name, last_error_detail)

    # -- All providers exhausted -> template fallback ----------------------
    enable_fallback = _get_llm_settings_field("enable_fallback", default=True)
    if not enable_fallback:
        logger.error("All LLM providers failed and fallback is disabled.")
        return LLMExplanation(
            text=(
                "LLM explanation failed and template fallback is disabled.  "
                "Please check your API keys and account balance."
            ),
            source="none",
            provider_used="none",
            is_fallback=True,
            error=last_error_detail,
        )

    logger.info("All LLM providers failed; generating template-based explanation.")
    text = _generate_template_explanation(context, explanation_type)
    explanation = LLMExplanation(
        text=text,
        source="template",
        provider_used="template",
        is_fallback=True,
        error=last_error_detail,
    )
    if cache_enabled:
        _cache.put(context, explanation_type, explanation)
    return explanation


# ═══════════════════════════════════════════════════════════════════════════
#  Provider Discovery (for GUI integration)
# ═══════════════════════════════════════════════════════════════════════════

def get_available_providers() -> List[Dict[str, Any]]:
    """
    Return metadata for all registered providers, with availability status.

    Designed to populate a GUI dropdown.  Each entry contains:

    - ``id``:            Provider identifier (``"groq"``, ``"deepseek"``, ...)
    - ``display_name``:  Human-readable label for the UI
    - ``available``:     ``True`` if the API key is configured
    - ``is_primary``:    ``True`` if this is currently the active primary
    - ``note``:          Short description (rate-limit info, etc.)

    Returns
    -------
    List[Dict[str, Any]]
        Ordered list, primary first, then by registry order.

    Example
    -------
    >>> get_available_providers()
    [
        {"id": "groq", "display_name": "Groq (Llama 3.3 70B)", "available": True, "is_primary": True, "note": "..."},
        {"id": "deepseek", "display_name": "DeepSeek", "available": True, "is_primary": False, "note": "..."},
        {"id": "openrouter", "display_name": "OpenRouter (Free)", "available": False, "is_primary": False, "note": "..."},
    ]
    """
    # Determine current primary
    current_primary = _get_runtime_primary()
    if current_primary is None:
        current_primary = _get_llm_settings_field("primary_provider", default="groq")

    results: List[Dict[str, Any]] = []
    for prov_id, info in _PROVIDER_REGISTRY.items():
        has_key = bool(os.getenv(info["env_key"], ""))
        results.append({
            "id": prov_id,
            "display_name": info["display_name"],
            "available": has_key,
            "is_primary": (prov_id == current_primary),
            "note": info["note"],
        })

    # Sort: primary first, then available providers, then unavailable
    results.sort(key=lambda r: (not r["is_primary"], not r["available"]))
    return results


def get_active_provider() -> str:
    """
    Return the name of the currently active primary provider.

    Respects runtime override > config > env > default.

    Returns
    -------
    str
        Provider identifier (e.g. ``"groq"``).
    """
    override = _get_runtime_primary()
    if override:
        return override
    return _get_llm_settings_field("primary_provider", default="groq")


# ═══════════════════════════════════════════════════════════════════════════
#  Convenience Helpers
# ═══════════════════════════════════════════════════════════════════════════

def clear_explanation_cache() -> None:
    """Clear the in-memory explanation cache."""
    _cache.clear()


def get_cache_size() -> int:
    """Return the number of cached explanations."""
    return _cache.size


def explain_descriptors(
    smiles: str,
    descriptors: Dict[str, Any],
    *,
    provider: Optional[str] = None,
    force_fallback: bool = False,
) -> LLMExplanation:
    """
    Shortcut: generate a descriptor-focused explanation.

    Parameters
    ----------
    smiles : str
        SMILES string of the molecule.
    descriptors : Dict[str, Any]
        Computed molecular descriptors.
    provider : Optional[str]
        Override primary provider for this call.
    force_fallback : bool
        Skip LLM and use template.

    Returns
    -------
    LLMExplanation
    """
    return generate_explanation(
        context={"smiles": smiles, "descriptors": descriptors},
        explanation_type="descriptor",
        provider=provider,
        force_fallback=force_fallback,
    )


def explain_docking(
    smiles: str,
    poses: List[Dict[str, Any]],
    interactions: List[Dict[str, Any]],
    *,
    provider: Optional[str] = None,
    force_fallback: bool = False,
) -> LLMExplanation:
    """
    Shortcut: generate a docking-result explanation.

    Parameters
    ----------
    smiles : str
        SMILES string of the ligand.
    poses : List[Dict[str, Any]]
        Docking pose records (must have at least ``affinity`` key).
    interactions : List[Dict[str, Any]]
        Protein-ligand interaction records.
    provider : Optional[str]
        Override primary provider for this call.
    force_fallback : bool
        Skip LLM and use template.

    Returns
    -------
    LLMExplanation

    Integration Note
    ----------------
    To use this for docking results, call from your docking workflow::

        from core.llm_utils import explain_docking

        explanation = explain_docking(
            smiles=ligand_smiles,
            poses=parsed_poses,
            interactions=mapped_interactions,
        )
        # explanation.text         -> rich LLM or template text
        # explanation.source       -> "groq" / "deepseek" / "template" / "cached"
        # explanation.provider_used -> which provider actually generated it

    This replaces direct calls to ``llm.docking_explainer`` and provides
    automatic fallback + caching.
    """
    return generate_explanation(
        context={
            "smiles": smiles,
            "poses": poses,
            "interactions": interactions,
        },
        explanation_type="docking",
        provider=provider,
        force_fallback=force_fallback,
    )


def explain_spectra(
    smiles: str,
    spectra: Dict[str, Any],
    *,
    provider: Optional[str] = None,
    force_fallback: bool = False,
) -> LLMExplanation:
    """
    Shortcut: generate a spectra-interpretation explanation.

    Parameters
    ----------
    smiles : str
        SMILES string of the molecule.
    spectra : Dict[str, Any]
        Spectral data keyed by domain (e.g., ``"IR"``, ``"1H_NMR"``).
    provider : Optional[str]
        Override primary provider for this call.
    force_fallback : bool
        Skip LLM and use template.

    Returns
    -------
    LLMExplanation
    """
    return generate_explanation(
        context={"smiles": smiles, "spectra": spectra},
        explanation_type="spectra",
        provider=provider,
        force_fallback=force_fallback,
    )


# ═══════════════════════════════════════════════════════════════════════════
#  Module Exports
# ═══════════════════════════════════════════════════════════════════════════

__all__ = [
    "LLMExplanation",
    "LLMErrorKind",
    "generate_explanation",
    "explain_descriptors",
    "explain_docking",
    "explain_spectra",
    "get_available_providers",
    "get_active_provider",
    "set_primary_provider",
    "reset_primary_provider",
    "clear_explanation_cache",
    "get_cache_size",
]
