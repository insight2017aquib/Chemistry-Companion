"""
api/routes/visualization.py
============================
REST endpoints for the Visualization module.
Returns HTTP 503 with a helpful message when dependencies are missing.
"""

from fastapi import APIRouter, File, UploadFile, HTTPException
from pydantic import BaseModel
from services.visualization_service import VisualizationService

router = APIRouter()


class LigandRequest(BaseModel):
    smiles: str


class ComplexRequest(BaseModel):
    protein_pdb: str
    ligand_pdbqt: str = ""
    ligand_mol_block: str = ""
    protein_format: str = "pdb"
    ligand_format: str = ""


def _require_viz():
    """Raise 503 if visualization deps are not installed."""
    if not VisualizationService.is_available():
        raise HTTPException(
            status_code=503,
            detail=VisualizationService.unavailable_message()
        )


@router.post("/protein")
async def visualize_protein(file: UploadFile = File(...)):
    _require_viz()
    filename = file.filename or "protein"
    if not filename.lower().endswith((".pdb", ".pdbqt")):
        raise HTTPException(400, "Only PDB or PDBQT files are supported.")

    content = (await file.read()).decode("utf-8")
    try:
        viewer_data = VisualizationService.process_protein(content, filename)
        return viewer_data.dict()
    except Exception as e:
        raise HTTPException(500, f"Error processing protein: {e}")


@router.post("/ligand2d")
async def visualize_ligand_2d(req: LigandRequest):
    _require_viz()
    try:
        viewer_data = VisualizationService.process_ligand(req.smiles)
        if not viewer_data.svg_2d:
            raise HTTPException(400, "Failed to render 2D ligand.")
        return {"svg": viewer_data.svg_2d}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error rendering 2D ligand: {e}")


@router.post("/ligand3d")
async def visualize_ligand_3d(req: LigandRequest):
    _require_viz()
    try:
        viewer_data = VisualizationService.process_ligand(req.smiles)
        if not viewer_data.html_3d or not (viewer_data.mol_block or viewer_data.pdbqt_content):
            raise HTTPException(400, "Failed to render 3D ligand.")
        return {
            "html": viewer_data.html_3d,
            "mol_block": viewer_data.mol_block,
            "pdbqt": viewer_data.pdbqt_content,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error rendering 3D ligand: {e}")


@router.post("/overlay")
async def visualize_overlay(req: ComplexRequest):
    _require_viz()
    try:
        ligand_structure = req.ligand_pdbqt or req.ligand_mol_block
        if not ligand_structure:
            raise HTTPException(400, "Ligand structure is required for overlay.")

        ligand_format = req.ligand_format or ("pdbqt" if req.ligand_pdbqt else "mol")
        viewer_data = VisualizationService.render_complex(
            req.protein_pdb,
            ligand_structure,
            protein_format=req.protein_format,
            ligand_format=ligand_format,
        )
        return {
            "html": viewer_data.html_3d,
            "protein_pdb": viewer_data.protein_pdb_content,
            "ligand_structure": viewer_data.ligand_pdbqt_content,
            "protein_format": viewer_data.protein_format,
            "ligand_format": viewer_data.ligand_format,
        }
    except Exception as e:
        raise HTTPException(500, f"Error generating overlay: {e}")
