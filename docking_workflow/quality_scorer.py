"""
docking_workflow/quality_scorer.py
==================================

Phase 8: Quality Scoring System for Receptors.

Produces a 0–100 quality score + human-readable label based on multiple
scientifically relevant factors for docking and virtual screening.

This is meant to help users quickly assess whether a structure is suitable
for serious docking work.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class QualityAssessment:
    score: float
    label: str
    breakdown: Dict[str, float]   # individual factor contributions
    notes: list[str]


def compute_quality_score(report: "ReceptorReport") -> QualityAssessment:
    from docking_workflow.protein_analysis import ReceptorReport  # avoid circular import
    """
    Main entry point for receptor quality scoring (Phase 8).

    Returns a QualityAssessment with:
    - score (0-100)
    - label (Excellent / Good / Acceptable / Poor)
    - breakdown of contributing factors
    - human-readable notes
    """
    breakdown: Dict[str, float] = {}
    notes: list[str] = []
    score = 50.0  # neutral starting point

    # --- Factor 1: Resolution (very important) ---
    res_score = 0.0
    if report.resolution:
        if report.resolution <= 1.8:
            res_score = 20
        elif report.resolution <= 2.2:
            res_score = 15
        elif report.resolution <= 2.5:
            res_score = 10
        elif report.resolution <= 3.0:
            res_score = 5
        else:
            res_score = -10
            notes.append(f"Low resolution ({report.resolution:.1f} Å) — structure may lack detail.")
    else:
        res_score = 0
        notes.append("No resolution information available.")

    breakdown["resolution"] = res_score
    score += res_score

    # --- Factor 2: Missing residues ---
    missing_penalty = 0.0
    missing_count = len(getattr(report, "missing_residues", []))
    if missing_count > 0:
        missing_penalty = min(missing_count * 2.5, 20)
        score -= missing_penalty
        breakdown["missing_residues"] = -missing_penalty
        notes.append(f"{missing_count} missing residues detected.")
    else:
        breakdown["missing_residues"] = 8
        score += 8

    # --- Factor 3: Ligand / Binding site quality ---
    ligand_bonus = 0.0
    if len(report.ligands) > 0:
        ligand_bonus = 12
        notes.append("Co-crystallized ligand(s) present — good for site definition.")
    elif len(getattr(report, "predicted_pockets", [])) > 0:  # if we ever attach this
        ligand_bonus = 6
    else:
        notes.append("No ligand or strong pocket information — site definition may be weaker.")

    breakdown["ligand_presence"] = ligand_bonus
    score += ligand_bonus

    # --- Factor 4: Cofactor & Metal integrity ---
    cofactor_score = 0.0
    if len(report.cofactors) > 0:
        cofactor_score += 5
    if len(report.metals) > 0:
        # Metals are a mixed bag — slight negative because they complicate scoring
        cofactor_score -= 3
        notes.append("Metal ions present — verify protonation and parameters for docking.")

    breakdown["cofactors_metals"] = cofactor_score
    score += cofactor_score

    # --- Factor 5: Chain quality ---
    chain_score = 0.0
    good_chains = sum(1 for c in report.chains if c.is_likely_protein and c.num_standard_aa > 50)
    if good_chains >= 1:
        chain_score = 8
    if len(report.chains) > 1 and good_chains == len(report.chains):
        chain_score += 5  # bonus for clean multi-chain

    breakdown["chain_quality"] = chain_score
    score += chain_score

    # --- Factor 6: Water situation (Phase 6 awareness) ---
    water_score = 0.0
    # We don't store water count in ReceptorReport yet in a structured way,
    # but we can give a small bonus if the report has good active-site water data in future.
    breakdown["water_handling"] = water_score

    # Clamp score
    final_score = max(0.0, min(100.0, round(score, 1)))

    # Determine label
    if final_score >= 85:
        label = "Excellent"
    elif final_score >= 70:
        label = "Good"
    elif final_score >= 50:
        label = "Acceptable"
    else:
        label = "Poor"

    if not notes:
        notes.append("No major structural red flags detected.")

    assessment = QualityAssessment(
        score=final_score,
        label=label,
        breakdown=breakdown,
        notes=notes
    )

    logger.info("Receptor quality assessment: %.1f (%s)", final_score, label)
    return assessment


def attach_quality_to_report(report: "ReceptorReport") -> "ReceptorReport":
    from docking_workflow.protein_analysis import ReceptorReport  # avoid circular import
    """Convenience helper to compute and attach quality to a ReceptorReport."""
    assessment = compute_quality_score(report)
    report.quality_score = assessment.score
    report.quality_label = assessment.label
    return report
