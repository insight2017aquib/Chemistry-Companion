"""
docking_workflow/interaction_mapper.py
======================================
Public API for protein-ligand interaction detection.

This module now delegates to the real geometric analyzer in
interaction_analyzer.py. The old hardcoded mocks have been removed.
"""

from dataclasses import dataclass
from typing import List, Optional

# Re-export the dataclass for backward compatibility
@dataclass
class Interaction:
    """Simple container for a detected interaction."""
    type: str  # "H-bond", "Hydrophobic", "Pi-Stacking", "Salt Bridge"
    protein_residue: str
    ligand_atom: str
    distance: float
    angle: Optional[float] = None  # None when no real geometry could be measured


def map_interactions(protein_pdb: str, pose_pdbqt: str) -> List[Interaction]:
    """
    Detects interactions between a protein (PDBQT) and a docked ligand pose.

    This is now a thin wrapper around the real geometry-based implementation.
    """
    from .interaction_analyzer import find_interactions
    return find_interactions(protein_pdb, pose_pdbqt, ligand_format="pdbqt")
