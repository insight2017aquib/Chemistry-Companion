import logging
from typing import Optional, List, Dict, Any
from core.visualization_utils import mol_to_svg_string
from rdkit import Chem

logger = logging.getLogger(__name__)

def render_ligand_2d(smiles: str, highlight_groups: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Renders a 2D SVG of a ligand SMILES.
    Uses existing core.visualization_utils.
    """
    mol = Chem.MolFromSmiles(smiles)
    if not mol:
        logger.error(f"Invalid SMILES for 2D rendering: {smiles}")
        return {"svg": "", "error": "Invalid SMILES"}
        
    try:
        svg_str = mol_to_svg_string(mol, size=(400, 300))
        return {"svg": svg_str, "error": None}
    except Exception as e:
        logger.exception("Error rendering 2D ligand")
        return {"svg": "", "error": str(e)}
