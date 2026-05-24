from typing import List, Dict, Any
from .pose_manager import DockingPose
from .interaction_mapper import Interaction

def build_docking_report(poses: List[DockingPose], interactions: List[Interaction]) -> Dict[str, Any]:
    """
    Assembles a JSON-serializable report of docking results.
    """
    report = {
        "num_poses": len(poses),
        "best_affinity": poses[0].affinity_kcal if poses else None,
        "poses": [
            {
                "rank": p.rank,
                "affinity": p.affinity_kcal,
                "rmsd_lb": p.rmsd_lb,
                "rmsd_ub": p.rmsd_ub
            } for p in poses
        ],
        "interactions": [
            {
                "type": i.type,
                "protein_residue": i.protein_residue,
                "ligand_atom": i.ligand_atom,
                "distance": i.distance
            } for i in interactions
        ]
    }
    return report
