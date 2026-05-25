from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ViewerStyle(BaseModel):
    cartoon: bool = True
    stick: bool = True
    surface: bool = False
    color_scheme: str = "chain" # chain, secondary_structure, spectrum, etc.

class ProteinViewerData(BaseModel):
    pdb_id: Optional[str] = None
    num_chains: int = 0
    num_residues: int = 0
    has_ligands: bool = False
    ligand_names: List[str] = Field(default_factory=list)
    structure_format: str = "pdb"
    pdb_content: str = "" # Full PDB content for rendering

class LigandViewerData(BaseModel):
    smiles: str
    svg_2d: str = ""
    html_3d: str = ""
    mol_block: str = ""
    pdbqt_content: str = ""
    highlight_groups: Optional[List[int]] = None

class ComplexViewerData(BaseModel):
    protein_pdb_content: str
    ligand_pdbqt_content: str
    protein_format: str = "pdb"
    ligand_format: str = "pdbqt"
    style: ViewerStyle = Field(default_factory=ViewerStyle)
    html_3d: str = ""
