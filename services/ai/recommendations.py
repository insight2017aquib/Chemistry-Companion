"""
services/ai/recommendations.py
================================
AI Recommendation Framework for protein preparation intelligence.

Provides five recommendation interfaces that return structured
``Recommendation`` objects.  Each function either delegates to an AI
provider (via ``AIProviderManager``) or returns a heuristic/stub result
when AI is unavailable.

Phase 01 Status
---------------
- ``recommend_chain``: **Implemented** — wraps existing AI chain
  recommendation logic from ``DockingWorkspaceService``.
- ``recommend_pocket``: **Interface defined** — stub implementation.
- ``recommend_waters``: **Interface defined** — stub implementation.
- ``recommend_cofactors``: **Interface defined** — stub implementation.
- ``recommend_metals``: **Interface defined** — stub implementation.

Usage
-----
::

    from services.ai.recommendations import recommend_chain, recommend_pocket

    rec = recommend_chain(analysis_dict, ligand_smiles="CCO")
    print(rec.recommendation)   # ["A"]
    print(rec.confidence)       # "high"
    print(rec.reasoning)        # "Chain A contains the active site..."

    rec = recommend_pocket(pdb_text)
    print(rec.confidence)       # "low"
    print(rec.reasoning)        # "Not yet implemented..."
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from services.ai.models import AIResponse, Recommendation
from services.ai.provider_manager import AIProviderManager

try:
    from services.docking_workspace_service import DockingWorkspaceService
except Exception:
    DockingWorkspaceService = None

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
#  recommend_chain — IMPLEMENTED (wraps existing logic)
# ═══════════════════════════════════════════════════════════════════════════

def recommend_chain(
    analysis_dict: Dict[str, Any],
    ligand_smiles: Optional[str] = None,
    target_name: Optional[str] = None,
) -> Recommendation:
    """
    Recommend the best protein chain(s) for docking using AI.

    Delegates to the existing ``DockingWorkspaceService.get_ai_chain_recommendation``
    which uses a 25-year expert docking scientist prompt.  Falls back to
    heuristic if LLM is unavailable.

    Parameters
    ----------
    analysis_dict : Dict[str, Any]
        Output from ``DockingWorkspaceService.analyze_protein()`` or
        ``analyze_receptor()`` — must contain ``"chains"`` and
        ``"recommendation"`` keys.
    ligand_smiles : Optional[str]
        SMILES of the ligand to dock (improves AI recommendation quality).
    target_name : Optional[str]
        User-provided target name or notes.

    Returns
    -------
    Recommendation
        - ``recommendation``: List of chain IDs (e.g. ``["A"]``)
        - ``confidence``: "high", "medium", or "low"
        - ``reasoning``: Expert scientific rationale
    """
    try:
        from services.docking_workspace_service import DockingWorkspaceService

        result = DockingWorkspaceService.get_ai_chain_recommendation(
            analysis_dict=analysis_dict,
            ligand_smiles=ligand_smiles,
            target_name=target_name,
        )

        return Recommendation(
            recommendation=result.get("recommended_chain_ids", []),
            confidence=result.get("confidence", "low"),
            reasoning=result.get("rationale", "No rationale provided."),
            provider_used=result.get("source"),
            metadata={
                "warnings": result.get("warnings", []),
                "source": result.get("source"),
            },
        )

    except ImportError:
        logger.warning("DockingWorkspaceService not available for chain recommendation.")
        # Fall back to heuristic from analysis_dict
        heuristic = analysis_dict.get("recommendation", {})
        return Recommendation(
            recommendation=heuristic.get("recommended_chain_ids", []),
            confidence="low",
            reasoning=(
                "AI chain recommendation unavailable (docking dependencies not installed). "
                "Using heuristic: " + heuristic.get("rationale", "no rationale available")
            ),
            provider_used=None,
            metadata={"source": "heuristic_fallback"},
        )

    except Exception as exc:
        logger.exception("Chain recommendation failed: %s", exc)
        heuristic = analysis_dict.get("recommendation", {})
        return Recommendation(
            recommendation=heuristic.get("recommended_chain_ids", []),
            confidence="low",
            reasoning=f"AI chain recommendation failed: {exc}. Using heuristic fallback.",
            provider_used=None,
            metadata={"source": "heuristic_fallback", "error": str(exc)},
        )


def _render_analysis_summary(analysis_dict: Optional[Dict[str, Any]]) -> str:
    if not analysis_dict:
        return "No protein analysis summary is available."

    lines: List[str] = []
    if total := analysis_dict.get("total_chains"):
        lines.append(f"Total chains: {total}")
    if residues := analysis_dict.get("total_residues"):
        lines.append(f"Total residues: {residues}")
    if waters := analysis_dict.get("total_waters"):
        lines.append(f"Total waters: {waters}")
    if cofactors := len(analysis_dict.get("cofactors", [])):
        lines.append(f"Detected cofactors: {cofactors}")
    if metals := len(analysis_dict.get("metals", [])):
        lines.append(f"Detected metals: {metals}")

    chains = analysis_dict.get("chains") or []
    if chains:
        chain_summaries = []
        for chain in chains[:4]:
            chain_summaries.append(
                f"{chain.get('chain_id', '?')}({chain.get('num_residues', 0)} res, "
                f"{'protein' if chain.get('is_likely_protein') else 'non-protein'})"
            )
        lines.append("Chains: " + ", ".join(chain_summaries))

    return "\n".join(lines)


def _build_ai_expert_prompt(
    domain: str,
    question: str,
    pdb_text: Optional[str] = None,
    analysis_dict: Optional[Dict[str, Any]] = None,
) -> str:
    domain_label = domain or "general"
    analysis_summary = _render_analysis_summary(analysis_dict)

    prompt = (
        "You are a senior protein preparation scientist and docking expert. "
        "The user is asking a request within the domain of: "
        f"{domain_label}.\n\n"
        "Provide a concise, evidence-based answer that references the available protein analysis "
        "and structural context. If raw PDB text is available, do not repeat the full PDB output verbatim."
    )

    if analysis_summary:
        prompt += f"\n\nProtein analysis summary:\n{analysis_summary}"

    if pdb_text:
        prompt += (
            "\n\nRaw PDB text is available but may be large. Focus on the detected features, "
            "recommended chains, waters, cofactors, metals, and pockets rather than repeating coordinates."
        )

    prompt += f"\n\nQuestion:\n{question}\n\nAnswer:" 
    return prompt


def _ask_expert(
    prompt: str,
    provider: Optional[str] = None,
    timeout: int = 30,
) -> AIResponse:
    manager = AIProviderManager()
    return manager.query(prompt, provider=provider, timeout=timeout)


def ask_expert(
    question: str,
    pdb_text: Optional[str] = None,
    analysis_dict: Optional[Dict[str, Any]] = None,
    domain: Optional[str] = "general",
    provider: Optional[str] = None,
) -> Recommendation:
    prompt = _build_ai_expert_prompt(domain or "general", question or "Please explain the protein preparation recommendations.", pdb_text, analysis_dict)
    response = _ask_expert(prompt, provider=provider)
    confidence = "low" if response.provider_used == "none" or response.error else "medium"
    return Recommendation(
        recommendation={"answer": response.text},
        confidence=confidence,
        reasoning=response.text or "No answer was returned by the AI expert.",
        provider_used=response.provider_used if response.provider_used != "none" else None,
        metadata={
            "provider_used": response.provider_used,
            "model_used": response.model_used,
            "latency_ms": response.latency_ms,
            "error": response.error,
            "domain": domain,
        },
    )


def recommend_pocket(
    pdb_text: str,
    analysis_dict: Optional[Dict[str, Any]] = None,
) -> Recommendation:
    """
    Recommend the best pocket for docking using AI-assisted pocket evaluation.
    """
    suggested_pockets = []
    pocket_tool = None
    pocket_error = None

    if DockingWorkspaceService is not None:
        try:
            pocket_data = DockingWorkspaceService.detect_pockets(pdb_text)
            suggested_pockets = pocket_data.get("suggestions", []) if isinstance(pocket_data, dict) else []
            pocket_tool = pocket_data.get("tool_used") if isinstance(pocket_data, dict) else None
        except Exception as exc:
            pocket_error = str(exc)
            logger.warning("Pocket recommendation helper failed: %s", exc)

    top_pocket = suggested_pockets[0] if suggested_pockets else None
    question = (
        "You are a pocket recommendation expert. Analyze the detected pockets and recommend the most druggable binding site "
        "for docking. Explain why the chosen pocket is preferred and provide a short druggability assessment."
    )
    ai_response = _ask_expert(_build_ai_expert_prompt("pocket", question, pdb_text, analysis_dict))
    reasoning = ai_response.text if ai_response.provider_used != "none" and not ai_response.error else (
        "No AI provider is configured or available. Use the detected detected pockets as a starting point and select the top-ranked site based on score and ligand proximity."
    )
    confidence = "medium" if ai_response.provider_used != "none" and not ai_response.error else ("low" if suggested_pockets else "low")
    return Recommendation(
        recommendation={
            "top_pocket": top_pocket,
            "all_pockets": suggested_pockets,
        },
        confidence=confidence,
        reasoning=reasoning,
        provider_used=ai_response.provider_used if ai_response.provider_used != "none" else None,
        metadata={
            "provider_error": ai_response.error,
            "tool_used": pocket_tool,
            "pocket_error": pocket_error,
        },
    )


def recommend_waters(
    pdb_text: str,
    analysis_dict: Optional[Dict[str, Any]] = None,
) -> Recommendation:
    """
    Recommend water handling strategy using AI assistance.
    """
    water_result: Dict[str, Any] = {}
    water_error = None

    if DockingWorkspaceService is not None:
        try:
            water_result = DockingWorkspaceService.classify_waters(pdb_text)
        except Exception as exc:
            water_error = str(exc)
            logger.warning("Water recommendation helper failed: %s", exc)

    question = (
        "You are a water handling expert for docking. Based on the receptor structure, recommend which waters should be retained "
        "for active-site interactions and which waters are likely bulk solvent artifacts. Explain your reasoning briefly."
    )
    ai_response = _ask_expert(_build_ai_expert_prompt("water", question, pdb_text, analysis_dict))
    reasoning = ai_response.text if ai_response.provider_used != "none" and not ai_response.error else (
        "No AI provider is configured or available. Analyze crystallographic waters near the binding site and retain those that bridge key interactions while removing bulk solvent molecules."
    )
    confidence = "medium" if ai_response.provider_used != "none" and not ai_response.error else "low"
    return Recommendation(
        recommendation={
            "waters": water_result.get("waters", []),
            "summary": water_result.get("summary", {}),
        },
        confidence=confidence,
        reasoning=reasoning,
        provider_used=ai_response.provider_used if ai_response.provider_used != "none" else None,
        metadata={
            "provider_error": ai_response.error,
            "water_error": water_error,
        },
    )


def recommend_cofactors(
    pdb_text: str,
    analysis_dict: Optional[Dict[str, Any]] = None,
) -> Recommendation:
    """
    Recommend cofactor handling using AI-assisted analysis.
    """
    if analysis_dict is None and DockingWorkspaceService is not None:
        try:
            analysis_dict = DockingWorkspaceService.analyze_receptor(pdb_text)
        except Exception:
            analysis_dict = analysis_dict

    cofactors = analysis_dict.get("cofactors", []) if analysis_dict else []
    question = (
        "You are a cofactor expert. Recommend which cofactors should be retained during docking preparation "
        "and which may be removed, based on biological relevance and ligand compatibility. Provide a short rationale."
    )
    ai_response = _ask_expert(_build_ai_expert_prompt("cofactor", question, pdb_text, analysis_dict))
    reasoning = ai_response.text if ai_response.provider_used != "none" and not ai_response.error else (
        "No AI provider is configured or available. Retain essential cofactors that participate in catalysis or ligand binding and remove crystallographic additives."
    )
    confidence = "medium" if ai_response.provider_used != "none" and not ai_response.error else "low"
    return Recommendation(
        recommendation={
            "cofactors": cofactors,
        },
        confidence=confidence,
        reasoning=reasoning,
        provider_used=ai_response.provider_used if ai_response.provider_used != "none" else None,
        metadata={
            "provider_error": ai_response.error,
        },
    )


def recommend_metals(
    pdb_text: str,
    analysis_dict: Optional[Dict[str, Any]] = None,
) -> Recommendation:
    """
    Recommend metal handling using AI-assisted analysis.
    """
    if analysis_dict is None and DockingWorkspaceService is not None:
        try:
            analysis_dict = DockingWorkspaceService.analyze_receptor(pdb_text)
        except Exception:
            analysis_dict = analysis_dict

    metals = analysis_dict.get("metals", []) if analysis_dict else []
    question = (
        "You are a metal coordination expert. Recommend which metal ions should be retained for docking "
        "and which are likely crystal artifacts. Explain the catalytic or structural importance of each retained metal."
    )
    ai_response = _ask_expert(_build_ai_expert_prompt("metal", question, pdb_text, analysis_dict))
    reasoning = ai_response.text if ai_response.provider_used != "none" and not ai_response.error else (
        "No AI provider is configured or available. Keep catalytic and structural metals that participate directly in the binding site, and remove weakly bound crystallographic ions."
    )
    confidence = "medium" if ai_response.provider_used != "none" and not ai_response.error else "low"
    return Recommendation(
        recommendation={
            "metals": metals,
        },
        confidence=confidence,
        reasoning=reasoning,
        provider_used=ai_response.provider_used if ai_response.provider_used != "none" else None,
        metadata={
            "provider_error": ai_response.error,
        },
    )


# ═══════════════════════════════════════════════════════════════════════════
#  Module Exports
# ═══════════════════════════════════════════════════════════════════════════

__all__ = [
    "Recommendation",
    "recommend_chain",
    "recommend_pocket",
    "recommend_waters",
    "recommend_cofactors",
    "recommend_metals",
]
