import math
from typing import List, Dict, Any, Optional
from .pose_manager import DockingPose
from .interaction_mapper import Interaction

# ΔG (kcal/mol) → pKd conversion at T = 298.15 K.
# ΔG = -RT ln(Kd)  ⇒  pKd = -log10(Kd) = -ΔG / (2.303 · R · T) = -ΔG / 1.364
_RT_LN10_KCAL = 1.364


def affinity_to_pkd(affinity_kcal: Optional[float]) -> Optional[float]:
    """Convert a Vina binding affinity (kcal/mol, negative) to an approximate pKd.

    This is the standard textbook conversion and is only a rough interpretability
    aid, not a measured potency. Returns None when affinity is missing/non-negative.
    """
    if affinity_kcal is None:
        return None
    try:
        if affinity_kcal >= 0:
            return None
        return round(-float(affinity_kcal) / _RT_LN10_KCAL, 2)
    except (TypeError, ValueError):
        return None


def build_docking_report(poses: List[DockingPose], interactions: List[Interaction]) -> Dict[str, Any]:
    """
    Assembles a JSON-serializable report of docking results.
    """
    report = {
        "num_poses": len(poses),
        "best_affinity": poses[0].affinity_kcal if poses else None,
        "best_pkd": affinity_to_pkd(poses[0].affinity_kcal) if poses else None,
        "poses": [
            {
                "rank": p.rank,
                "affinity": p.affinity_kcal,
                "pkd": affinity_to_pkd(p.affinity_kcal),
                "rmsd_lb": p.rmsd_lb,
                "rmsd_ub": p.rmsd_ub
            } for p in poses
        ],
        # Clarify what rmsd_lb/rmsd_ub actually mean: these are Vina's internal
        # RMSDs of each pose relative to the top-ranked pose, NOT RMSD to a
        # reference/crystal ligand. Redocking validation (redock_validation.py)
        # reports the latter separately under the "validation" key.
        "rmsd_note": (
            "rmsd_lb / rmsd_ub are Vina inter-pose RMSDs relative to the best pose, "
            "not RMSD to a reference/crystal ligand."
        ),
        "interactions": [
            {
                "type": i.type,
                "protein_residue": i.protein_residue,
                "ligand_atom": i.ligand_atom,
                "distance": i.distance,
                "angle": i.angle
            } for i in interactions
        ]
    }
    return report
