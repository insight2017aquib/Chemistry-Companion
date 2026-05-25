from typing import Optional, Dict, Any
from .viewer_models import ProteinViewerData, LigandViewerData, ComplexViewerData
from .protein_loader import load_protein_pdb
from .ligand_renderer_2d import render_ligand_2d
from .ligand_renderer_3d import generate_ligand_mol_block, render_ligand_3d
from .complex_renderer import render_protein_ligand_complex

class VisualizationOrchestrator:
    """
    Orchestrates the visualization module operations.
    """
    
    @staticmethod
    def process_protein(pdb_text: str, filename: Optional[str] = None) -> ProteinViewerData:
        return load_protein_pdb(pdb_text, filename)
        
    @staticmethod
    def process_ligand(smiles: str) -> LigandViewerData:
        svg_result = render_ligand_2d(smiles)
        html_3d = render_ligand_3d(smiles)
        mol_block = generate_ligand_mol_block(smiles)
        
        # Prepare the ligand 3D coordinate model in PDBQT format
        from core.docking_preparation import prepare_docking_structure
        try:
            pdbqt = prepare_docking_structure(smiles)
        except Exception:
            pdbqt = ""
            
        return LigandViewerData(
            smiles=smiles,
            svg_2d=svg_result.get("svg", ""),
            html_3d=html_3d,
            mol_block=mol_block,
            pdbqt_content=pdbqt
        )
        
    @staticmethod
    def render_complex(
        protein_pdb: str,
        ligand_structure: str,
        protein_format: str = "pdb",
        ligand_format: str = "pdbqt",
    ) -> ComplexViewerData:
        html_3d = render_protein_ligand_complex(
            protein_pdb,
            ligand_structure,
            protein_format=protein_format,
            ligand_format=ligand_format,
        )
        
        return ComplexViewerData(
            protein_pdb_content=protein_pdb,
            ligand_pdbqt_content=ligand_structure,
            protein_format=protein_format,
            ligand_format=ligand_format,
            html_3d=html_3d
        )
