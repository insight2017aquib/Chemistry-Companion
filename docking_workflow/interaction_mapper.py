from dataclasses import dataclass
from typing import List

@dataclass
class Interaction:
    type: str # "H-bond", "Hydrophobic", "Pi-Stacking", "Salt Bridge"
    protein_residue: str
    ligand_atom: str
    distance: float
    angle: float = 0.0

def map_interactions(protein_pdb: str, pose_pdbqt: str) -> List[Interaction]:
    """
    Detects interactions between protein and ligand.
    For now, this returns a mock mapping, since full spatial interaction mapping 
    requires a dedicated package like ProLIF or MDAnalysis.
    """
    # Placeholder for actual interaction mapping logic
    return [
        Interaction("H-bond", "SER 45", "O1", 2.8),
        Interaction("Hydrophobic", "PHE 120", "C4", 3.5)
    ]
