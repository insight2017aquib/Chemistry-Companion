"""
docking_workflow/water_analysis.py
==================================

Phase 6: Water Analysis for Receptor Preparation.

Classifies water molecules into categories and provides
Keep / Remove recommendations based on proximity to binding sites.

Categories:
- active_site : Close to ligand or predicted pocket (high chance of functional relevance)
- bulk        : Far from binding sites (usually safe to remove)
- conserved   : (Basic heuristic) Buried / low solvent exposure waters (advanced, partial support)

This module is designed to work together with ReceptorReport from Phase 1.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

from docking_workflow.protein_analysis import (
    ReceptorReport,
    LigandInfo,
    _parse_with_gemmi,
    _fallback_line_parser,
)

logger = logging.getLogger(__name__)


@dataclass
class WaterInfo:
    """Information about a single water molecule."""
    chain_id: str
    resnum: int
    x: float
    y: float
    z: float
    category: str                 # "active_site", "bulk", "conserved"
    distance_to_site: Optional[float] = None   # distance to nearest ligand/pocket
    recommendation: str = "remove"             # "keep" or "remove"
    reason: str = ""


def _extract_waters_from_gemmi(pdb_text: str) -> List[Dict[str, Any]]:
    """Extract water coordinates using gemmi."""
    try:
        import gemmi
        st = gemmi.read_structure_string(pdb_text)
    except Exception:
        return []

    waters = []
    for model in st:
        for chain in model:
            for res in chain:
                if res.name.upper() in {"HOH", "WAT", "H2O", "WTR"}:
                    for atom in res:
                        if atom.name.strip().upper() in {"O", "OW"}:
                            pos = atom.pos
                            waters.append({
                                "chain_id": chain.name or "_",
                                "resnum": int(res.seqid.num),
                                "x": pos.x,
                                "y": pos.y,
                                "z": pos.z
                            })
    return waters


def _extract_waters_fallback(pdb_text: str) -> List[Dict[str, Any]]:
    """Fallback pure-Python water extraction."""
    waters = []
    for line in pdb_text.splitlines():
        if line.startswith(("ATOM", "HETATM")):
            try:
                resname = line[17:20].strip().upper()
                if resname in {"HOH", "WAT", "H2O", "WTR"}:
                    chain_id = line[21:22].strip() or "_"
                    resnum = int(line[22:26].strip())
                    x = float(line[30:38])
                    y = float(line[38:46])
                    z = float(line[46:54])
                    waters.append({
                        "chain_id": chain_id,
                        "resnum": resnum,
                        "x": x,
                        "y": y,
                        "z": z
                    })
            except Exception:
                continue
    return waters


def _extract_protein_atom_positions(pdb_text: str) -> List[tuple[float, float, float]]:
    """Extract protein atom positions from PDB for water burial heuristics."""
    positions = []
    for line in pdb_text.splitlines():
        if line.startswith("ATOM"):
            try:
                resname = line[17:20].strip().upper()
                if resname in {"HOH", "WAT", "H2O", "WTR"}:
                    continue
                x = float(line[30:38])
                y = float(line[38:46])
                z = float(line[46:54])
                positions.append((x, y, z))
            except Exception:
                continue
    return positions


def classify_waters(
    pdb_text: str,
    report: ReceptorReport,
    active_site_cutoff: float = 5.0,
    conserved_buried_threshold: float = 3.5
) -> List[WaterInfo]:
    """
    Classify all water molecules and assign Keep/Remove recommendations.

    Logic:
    - If water is within `active_site_cutoff` of any ligand or pocket center → active_site
    - Else → bulk
    - Basic "conserved" heuristic: very close waters that might be buried (simplified)
    """
    # Get water coordinates
    waters = _extract_waters_from_gemmi(pdb_text)
    if not waters:
        waters = _extract_waters_fallback(pdb_text)

    if not waters:
        return []

    # Collect all important site centers (ligands + predicted pockets)
    site_centers = []

    # From ligands (Phase 3A)
    for ligand in getattr(report, "ligands", []):
        if hasattr(ligand, "centroid") and ligand.centroid:
            site_centers.append(ligand.centroid)

    protein_atoms = _extract_protein_atom_positions(pdb_text)
    classified_waters: List[WaterInfo] = []

    for w in waters:
        wx, wy, wz = w["x"], w["y"], w["z"]

        min_dist = float("inf")
        for center in site_centers:
            if isinstance(center, dict):
                cx, cy, cz = center.get("x", 0), center.get("y", 0), center.get("z", 0)
            else:
                cx = getattr(center, "x", 0)
                cy = getattr(center, "y", 0)
                cz = getattr(center, "z", 0)

            dist = ((wx - cx) ** 2 + (wy - cy) ** 2 + (wz - cz) ** 2) ** 0.5
            if dist < min_dist:
                min_dist = dist

        nearby_protein_atoms = 0
        for px, py, pz in protein_atoms:
            d = ((wx - px) ** 2 + (wy - py) ** 2 + (wz - pz) ** 2) ** 0.5
            if d <= conserved_buried_threshold:
                nearby_protein_atoms += 1

        if site_centers and min_dist <= active_site_cutoff:
            category = "active_site"
            recommendation = "keep"
            reason = f"Within {active_site_cutoff}Å of binding site (dist={min_dist:.1f}Å)"
        elif nearby_protein_atoms >= 6:
            category = "conserved"
            recommendation = "keep"
            reason = f"Buried conserved water with {nearby_protein_atoms} nearby protein atoms."
        else:
            category = "bulk"
            recommendation = "remove"
            if min_dist != float("inf"):
                reason = f"Bulk solvent (dist to nearest site = {min_dist:.1f}Å)"
            else:
                reason = "Bulk solvent with no nearby binding site information."

        classified_waters.append(
            WaterInfo(
                chain_id=w["chain_id"],
                resnum=w["resnum"],
                x=wx,
                y=wy,
                z=wz,
                category=category,
                distance_to_site=round(min_dist, 2) if min_dist != float("inf") else None,
                recommendation=recommendation,
                reason=reason
            )
        )

    logger.info(
        "Classified %d waters: active_site=%d, bulk=%d",
        len(classified_waters),
        sum(1 for w in classified_waters if w.category == "active_site"),
        sum(1 for w in classified_waters if w.category == "bulk")
    )

    return classified_waters


def get_water_summary(waters: List[WaterInfo]) -> Dict[str, Any]:
    """Convenience summary for API responses."""
    active = [w for w in waters if w.category == "active_site"]
    bulk = [w for w in waters if w.category == "bulk"]

    return {
        "total_waters": len(waters),
        "active_site_waters": len(active),
        "bulk_waters": len(bulk),
        "recommended_keep": len(active),
        "recommended_remove": len(bulk),
    }
