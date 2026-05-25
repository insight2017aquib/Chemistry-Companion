"""
api/routes/docking_workspace.py
================================
REST endpoints for the Docking Workspace module.
Returns HTTP 503 with a helpful message when dependencies are missing.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.docking_workspace_service import DockingWorkspaceService

router = APIRouter()


# ── Request Models ──────────────────────────────────────────────

class ProteinPrepareRequest(BaseModel):
    pdb_text: str
    remove_water: bool = True
    add_charges: bool = True

class GridboxRequest(BaseModel):
    pdbqt_text: str

class DockingRunRequest(BaseModel):
    protein_pdbqt: str
    ligand_pdbqt: str
    center_x: float
    center_y: float
    center_z: float
    size_x: float
    size_y: float
    size_z: float
    exhaustiveness: int = 8
    num_modes: int = 9

class PoseRequest(BaseModel):
    job_id: str
    rank: int

class InteractionsRequest(BaseModel):
    job_id: str
    rank: int


# ── Guard ───────────────────────────────────────────────────────

def _require_docking():
    """Raise 503 if docking deps are not installed."""
    if not DockingWorkspaceService.is_available():
        raise HTTPException(
            status_code=503,
            detail=DockingWorkspaceService.unavailable_message()
        )


# ── Endpoints ───────────────────────────────────────────────────

@router.post("/protein_prepare")
async def protein_prepare(req: ProteinPrepareRequest):
    _require_docking()
    try:
        pdbqt_text = DockingWorkspaceService.prepare_protein(
            req.pdb_text, req.remove_water, req.add_charges
        )
        return {"pdbqt": pdbqt_text}
    except Exception as e:
        raise HTTPException(400, f"Protein preparation failed: {e}")


@router.post("/gridbox")
async def calculate_gridbox(req: GridboxRequest):
    _require_docking()
    try:
        config = DockingWorkspaceService.calculate_gridbox(req.pdbqt_text)
        return config.__dict__
    except Exception as e:
        raise HTTPException(400, f"Grid box calculation failed: {e}")


@router.post("/run")
async def run_docking(req: DockingRunRequest):
    _require_docking()
    try:
        job_id = DockingWorkspaceService.create_job()
        report = DockingWorkspaceService.run_docking(
            job_id, req.protein_pdbqt, req.ligand_pdbqt,
            req.center_x, req.center_y, req.center_z,
            req.size_x, req.size_y, req.size_z,
            req.exhaustiveness, req.num_modes
        )
        return {"job_id": job_id, "report": report}
    except Exception as e:
        raise HTTPException(500, f"Docking execution failed: {e}")


@router.post("/pose")
async def get_pose(req: PoseRequest):
    _require_docking()
    try:
        pose_data = DockingWorkspaceService.get_pose(req.job_id, req.rank)
        return {"pose": pose_data}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(400, f"Pose retrieval failed: {e}")


@router.post("/interactions")
async def get_interactions(req: InteractionsRequest):
    _require_docking()
    try:
        interactions = DockingWorkspaceService.get_interactions(req.job_id, req.rank)
        return {"interactions": interactions}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(400, f"Interaction mapping failed: {e}")
