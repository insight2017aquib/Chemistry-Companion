"""
docking_workflow/interaction_fingerprint.py
============================================
Compare a docked pose's interactions against a reference ligand's interactions
(Advanced Docking P3).

The existing interaction_analyzer already detects H-bonds, hydrophobic contacts,
pi-stacking, salt bridges, metal coordination and water bridges with real geometry.
This module turns that into a *decision* signal: given the co-crystal ligand's
interactions and a docked pose's interactions, it reports how many of the key
contacts the pose reproduces, which it misses, and which are new — plus a single
Tanimoto similarity score. A pose that reproduces the native contacts is far more
trustworthy than one with a similar score but different contacts.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Iterable, Tuple

logger = logging.getLogger(__name__)

_WATER_SUFFIX = re.compile(r"\s*\(via water.*?\)", re.IGNORECASE)


def _interaction_fields(item: Any) -> Tuple[str, str]:
    """Accept either an Interaction dataclass or a dict; return (type, residue)."""
    if isinstance(item, dict):
        return str(item.get("type", "")), str(item.get("protein_residue", ""))
    return str(getattr(item, "type", "")), str(getattr(item, "protein_residue", ""))


def _normalize_type(itype: str) -> str:
    """Collapse geometric sub-variants so parallel/T-shaped pi-stacking match, etc."""
    t = itype.strip().lower()
    if t.startswith("pi-stacking"):
        return "pi-stacking"
    if t.startswith("h-bond") or t.startswith("hydrogen"):
        return "h-bond"
    if t.startswith("hydrophobic"):
        return "hydrophobic"
    if "salt" in t:
        return "salt-bridge"
    if "metal" in t:
        return "metal"
    if "water" in t:
        return "water-bridge"
    return t


def _normalize_residue(residue: str) -> str:
    """Strip water-bridge annotations and normalize whitespace."""
    return _WATER_SUFFIX.sub("", residue or "").strip().upper()


def fingerprint(interactions: Iterable[Any]) -> set[Tuple[str, str]]:
    """Build a set of (interaction_type, residue) keys from an interaction list."""
    fp: set[Tuple[str, str]] = set()
    for item in interactions or []:
        itype, residue = _interaction_fields(item)
        residue = _normalize_residue(residue)
        if not residue:
            continue
        fp.add((_normalize_type(itype), residue))
    return fp


@dataclass
class FingerprintComparison:
    similarity: float                       # Tanimoto over (type, residue) keys, 0-1
    reproduced: List[Dict[str, str]] = field(default_factory=list)
    missed: List[Dict[str, str]] = field(default_factory=list)
    new: List[Dict[str, str]] = field(default_factory=list)
    reference_count: int = 0
    pose_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "similarity": round(self.similarity, 3),
            "reproduced": self.reproduced,
            "missed": self.missed,
            "new": self.new,
            "reference_count": self.reference_count,
            "pose_count": self.pose_count,
        }


def _as_records(keys: Iterable[Tuple[str, str]]) -> List[Dict[str, str]]:
    return [{"type": t, "residue": r} for t, r in sorted(keys)]


def compare_interactions(reference: Iterable[Any], pose: Iterable[Any]) -> FingerprintComparison:
    """Compare reference (co-crystal ligand) vs. docked pose interaction fingerprints."""
    ref_fp = fingerprint(reference)
    pose_fp = fingerprint(pose)

    if not ref_fp and not pose_fp:
        similarity = 0.0
    else:
        inter = ref_fp & pose_fp
        union = ref_fp | pose_fp
        similarity = len(inter) / len(union) if union else 0.0

    return FingerprintComparison(
        similarity=similarity,
        reproduced=_as_records(ref_fp & pose_fp),
        missed=_as_records(ref_fp - pose_fp),
        new=_as_records(pose_fp - ref_fp),
        reference_count=len(ref_fp),
        pose_count=len(pose_fp),
    )


def reference_ligand_interactions(pdb_text: str, protein_pdbqt: str,
                                  resname: str, chain: str, resnum: int) -> List[Any]:
    """Compute the co-crystal ligand's own interactions with the receptor.

    Extracts the ligand, converts it to PDBQT (for AutoDock atom typing), and runs
    the standard interaction analyzer against the prepared receptor.
    """
    from docking_workflow.redock_validation import extract_ligand_block
    from docking_workflow.interaction_analyzer import find_interactions
    from core.openbabel_utils import convert_format

    ligand_pdb = extract_ligand_block(pdb_text, resname, chain, resnum)
    try:
        ligand_pdbqt = convert_format(ligand_pdb, "pdb", "pdbqt")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not convert reference ligand to PDBQT: %s", exc)
        return []
    return find_interactions(protein_pdbqt, ligand_pdbqt, ligand_format="pdbqt")


__all__ = [
    "fingerprint",
    "compare_interactions",
    "reference_ligand_interactions",
    "FingerprintComparison",
]
