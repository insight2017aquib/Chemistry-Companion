"""
api/routes/docking_workspace.py
================================
REST endpoints for the Docking Workspace module.
Returns HTTP 503 with a helpful message when dependencies are missing.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from database.models import get_db
from services.docking_workspace_service import DockingWorkspaceService
from services.ai import (
    ask_expert,
    recommend_pocket,
    recommend_waters,
    recommend_cofactors,
    recommend_metals,
)

# Import shared docking schemas (Phase 1+)
try:
    from api.schemas.docking import (
        ProteinAnalyzeRequest,
        ProteinAnalysisResult,
        ProteinChainsResult,
        ProteinWatersResult,
        ProteinCofactorsResult,
        ProteinMetalsResult,
        ProteinQualityResult,
    )
except Exception:
    # Fallback so the router can still load even if schemas have issues
    ProteinAnalyzeRequest = None
    ProteinAnalysisResult = None
    ProteinChainsResult = None
    ProteinWatersResult = None
    ProteinCofactorsResult = None
    ProteinMetalsResult = None
    ProteinQualityResult = None

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Request Models ──────────────────────────────────────────────

class ProteinPrepareRequest(BaseModel):
    pdb_text: str
    remove_water: bool = True
    add_charges: bool = True

    # Phase 4/5: Advanced preparation options
    keep_cofactors: bool = False
    keep_metals: bool = False
    keep_active_site_waters: bool = False
    remove_bulk_waters: bool = True
    # Co-crystal ligand removal (default on — a docking receptor must have an empty pocket)
    remove_ligands: bool = True

    # Phase 7: Protonation
    run_protonation: bool = False
    ph: float = 7.4

    # PAMS: dock by asset reference. If pdb_text is empty, resolve from this asset;
    # the prepared receptor PDBQT is written back onto the asset (asset-native docking).
    asset_id: Optional[str] = None

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
    scoring_function: str = "vina"
    seed: Optional[int] = None
    # Phase 1: optional pre-docking protein analysis metadata
    selected_chains: list[str] | None = None
    protein_analysis_summary: dict | None = None
    receptor_name: str | None = None
    ligand_name: str | None = None

class PoseRequest(BaseModel):
    job_id: str
    rank: int

class InteractionsRequest(BaseModel):
    job_id: str
    rank: int

# ── Advanced Docking P1/P2/P4/P5 request models ──────────────────────

class RedockValidateRequest(BaseModel):
    pdb_text: str
    resname: Optional[str] = None
    chain: Optional[str] = None
    resnum: Optional[int] = None
    exhaustiveness: int = 8
    num_modes: int = 9
    scoring_function: str = "vina"
    seed: Optional[int] = None
    remove_water: bool = True

class LigandPrepRequest(BaseModel):
    smiles: str
    ph: Optional[float] = None
    enumerate_protonation: bool = False
    enumerate_tautomers: bool = False
    enumerate_stereo: bool = False
    n_conformers: int = 1
    prefer_meeko: bool = True

class BatchLigand(BaseModel):
    smiles: str
    name: Optional[str] = None

class BatchRunRequest(BaseModel):
    protein_pdbqt: str
    ligands: list[BatchLigand]
    center_x: float
    center_y: float
    center_z: float
    size_x: float
    size_y: float
    size_z: float
    exhaustiveness: int = 8
    num_modes: int = 9
    scoring_function: str = "vina"
    seed: Optional[int] = None
    ligand_prep_options: Optional[Dict[str, Any]] = None
    reference_interactions: Optional[list[Dict[str, Any]]] = None

class RescoreRequest(BaseModel):
    job_id: str
    rank: int = 1
    scoring_function: str = "vinardo"


# ── Guard ───────────────────────────────────────────────────────

def _require_docking():
    """Raise 503 if docking deps are not installed."""
    if not DockingWorkspaceService.is_available():
        raise HTTPException(
            status_code=503,
            detail=DockingWorkspaceService.unavailable_message()
        )


# ── PAMS bridge (asset-native docking; docking depends on PAMS, not vice-versa) ──

def _pams_service():
    try:
        from api.routes.proteins import get_service
        return get_service()
    except Exception as exc:  # noqa: BLE001
        logger.debug("PAMS service unavailable: %s", exc)
        return None


def _resolve_structure_text(pdb_text: Optional[str], asset_id: Optional[str]) -> str:
    """Prefer explicit pdb_text (backward compatible); otherwise resolve it from a
    PAMS asset. Returns '' if neither is available (caller errors clearly)."""
    if pdb_text and pdb_text.strip():
        return pdb_text
    if asset_id:
        svc = _pams_service()
        if svc is not None:
            text = svc.get_structure_text(asset_id)
            if text:
                return text
    return pdb_text or ""


def _writeback_prepared_receptor(asset_id: Optional[str], pdbqt: str, options: Optional[dict] = None) -> None:
    """Best-effort: persist the prepared receptor onto the asset and advance its
    lifecycle. Never breaks preparation if PAMS is unavailable."""
    if not asset_id or not pdbqt:
        return
    svc = _pams_service()
    if svc is None:
        return
    try:
        svc.attach_prepared_receptor(asset_id, pdbqt, options=options)
    except Exception as exc:  # noqa: BLE001
        logger.warning("PAMS write-back of prepared receptor failed for %s: %s", asset_id, exc)


# ── Endpoints ───────────────────────────────────────────────────

@router.post("/protein_prepare")
async def protein_prepare(req: ProteinPrepareRequest):
    _require_docking()
    try:
        pdb_text = _resolve_structure_text(req.pdb_text, req.asset_id)
        # Use rich preparation whenever any advanced option is requested (retention
        # flags or protonation) — all of these are only implemented in the rich path.
        options = None
        if (
            req.keep_cofactors
            or req.keep_metals
            or req.keep_active_site_waters
            or not req.remove_bulk_waters
            or not req.remove_ligands
            or req.run_protonation
        ):
            options = {
                "remove_water": req.remove_water,
                "add_charges": req.add_charges,
                "keep_cofactors": req.keep_cofactors,
                "keep_metals": req.keep_metals,
                "keep_active_site_waters": req.keep_active_site_waters,
                "remove_bulk_waters": req.remove_bulk_waters,
                "remove_ligands": req.remove_ligands,
                "run_protonation": req.run_protonation,
                "ph": req.ph,
            }
            pdbqt = DockingWorkspaceService.prepare_receptor_with_options(pdb_text, options)
        else:
            pdbqt = DockingWorkspaceService.prepare_protein(
                pdb_text, req.remove_water, req.add_charges
            )
        # Asset-native: write the prepared receptor back onto the PAMS asset so it
        # accumulates its derived artifacts and advances to DOCKING_READY.
        _writeback_prepared_receptor(req.asset_id, pdbqt, options=options)
        return {"pdbqt": pdbqt, "asset_id": req.asset_id}
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


# ── Reusable-receptor Workspace mirroring (Virtual Screening integration) ────
def _receptor_identity(req_dict: dict) -> str:
    """Deterministic identity for a prepared receptor configuration.

    A Workspace represents a *reusable prepared receptor*, keyed by the receptor,
    its selected chains, its preparation (captured by hashing the prepared PDBQT,
    which is the output of preparing those chains with the chosen options), and the
    grid. Same identity → same reusable receptor; a different chain selection,
    preparation, or grid yields a different identity."""
    import hashlib
    import json as _json

    pdbqt = req_dict.get("protein_pdbqt") or ""
    key_src = {
        "receptor": (req_dict.get("receptor_name") or "").strip().lower(),
        "chains": sorted(req_dict.get("selected_chains") or []),
        "pdbqt": hashlib.sha1(pdbqt.encode("utf-8", errors="replace")).hexdigest(),
        "grid": {k: req_dict.get(k) for k in
                 ("center_x", "center_y", "center_z", "size_x", "size_y", "size_z")},
    }
    return hashlib.sha1(_json.dumps(key_src, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _mirror_docking_to_workspace(db, job_id: str, req_dict: dict, report: dict) -> None:
    """Mirror a completed docking into the `workspaces` table so Virtual Screening
    (which consumes prepared-receptor Workspaces) can discover it.

    Reuses services.workspace_manager (no duplicated persistence logic). Updates an
    existing Workspace when the prepared-receptor configuration matches, otherwise
    creates a new one. Best-effort: never breaks docking completion."""
    import os
    from database.models import Workspace
    from services import workspace_manager

    receptor_name = req_dict.get("receptor_name") or f"receptor_{job_id[:8]}"
    identity = _receptor_identity(req_dict)

    state = {
        "proteinFileName": receptor_name,
        "selectedChains": req_dict.get("selected_chains") or [],
        "grid": {k: req_dict.get(k) for k in
                 ("center_x", "center_y", "center_z", "size_x", "size_y", "size_z")},
        "exhaustiveness": req_dict.get("exhaustiveness"),
        "scoringFunction": req_dict.get("scoring_function"),
        "receptor_identity": identity,
        "docking_job_id": job_id,
        "source": "job_manager",
    }
    heavy_data = {
        "proteinPdbqt": req_dict.get("protein_pdbqt") or "",
        "ligandPdbqt": req_dict.get("ligand_pdbqt") or "",
        "report": report,
        "jobId": job_id,
    }

    existing = next(
        (w for w in db.query(Workspace).filter(Workspace.module == "docking").all()
         if (w.state or {}).get("receptor_identity") == identity),
        None,
    )
    if existing is not None:
        result = workspace_manager.update_workspace(
            db, existing.id, state=state, heavy_data=heavy_data, name=f"Docking: {receptor_name}"
        )
    else:
        result = workspace_manager.create_workspace(
            db, name=f"Docking: {receptor_name}", module="docking", state=state, heavy_data=heavy_data
        )

    # Drop a real receptor.pdbqt next to heavy_data.json so Virtual Screening's
    # derived receptor path (start_screening) resolves to an actual file.
    file_path = (result or {}).get("file_path")
    if file_path and (req_dict.get("protein_pdbqt") or ""):
        receptor_path = os.path.join(os.path.dirname(file_path), "receptor.pdbqt")
        with open(receptor_path, "w", encoding="utf-8") as f:
            f.write(req_dict["protein_pdbqt"])


# ── Background runner (keeps the existing heavy logic unchanged) ─────────────
def _run_docking_in_background(job_id: str, req_dict: dict):
    """Executed via BackgroundTasks. Does the real work and persists the result."""
    from database.models import SessionLocal
    db = SessionLocal()
    try:
        logger.info(
            "Background _run_docking starting Vina for job=%s (prot=%dB, lig=%dB, grid center=(%s,%s,%s))",
            job_id,
            len(req_dict.get("protein_pdbqt") or ""),
            len(req_dict.get("ligand_pdbqt") or ""),
            req_dict.get("center_x"), req_dict.get("center_y"), req_dict.get("center_z"),
        )
        report = DockingWorkspaceService.run_docking(
            job_id,
            req_dict["protein_pdbqt"],
            req_dict["ligand_pdbqt"],
            req_dict["center_x"], req_dict["center_y"], req_dict["center_z"],
            req_dict["size_x"], req_dict["size_y"], req_dict["size_z"],
            req_dict.get("exhaustiveness", 8),
            req_dict.get("num_modes", 9),
            scoring_function=req_dict.get("scoring_function", "vina"),
            seed=req_dict.get("seed"),
        )

        # Attach optional metadata
        if req_dict.get("selected_chains") or req_dict.get("protein_analysis_summary"):
            report.setdefault("protein_preparation", {})
            report["protein_preparation"]["selected_chains"] = req_dict.get("selected_chains") or []
            if req_dict.get("protein_analysis_summary"):
                report["protein_preparation"]["analysis"] = req_dict["protein_analysis_summary"]

        # Persist (this also marks it completed via the existing save method)
        try:
            service = DockingWorkspaceService()
            service.save_docking_job(
                db,
                job_id=job_id,
                report=report,
                grid_config=report.get("grid_config"),
                receptor_name=req_dict.get("receptor_name"),
                ligand_name=req_dict.get("ligand_name"),
            )
        except Exception as db_err:
            logger.warning("Background: Failed to persist DockingJob %s (non-fatal): %s", job_id, db_err)

        # Mirror this completed docking into a reusable prepared-receptor Workspace so
        # Virtual Screening can discover it (update-or-create by receptor configuration).
        try:
            _mirror_docking_to_workspace(db, job_id, req_dict, report)
        except Exception as ws_err:
            logger.warning("Background: Failed to mirror DockingJob %s into a Workspace (non-fatal): %s", job_id, ws_err)

        logger.info("Background docking job %s completed successfully.", job_id)

    except Exception as exc:
        logger.exception("Background docking job %s failed: %s", job_id, exc)
        # Best-effort: mark the DB record as failed if it exists
        try:
            from database.models import DockingJob as DBDockingJob
            job = db.query(DBDockingJob).filter_by(id=job_id).first()
            if job:
                job.status = "failed"
                job.error_message = str(exc)[:500]
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.post("/run")
async def run_docking(req: DockingRunRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    NON-BLOCKING version.
    Returns immediately with a job_id. The heavy Vina work runs in the background.
    Frontend should poll GET /api/docking/job/{job_id} until the report appears.
    """
    _require_docking()
    try:
        job_id = DockingWorkspaceService.create_job()
        logger.info(
            "Docking /run received: job=%s, prot_len=%d, lig_len=%d, grid=(%.2f,%.2f,%.2f / %.1fx%.1fx%.1f), exhaust=%s, modes=%s",
            job_id,
            len(getattr(req, 'protein_pdbqt', '') or ''),
            len(getattr(req, 'ligand_pdbqt', '') or ''),
            req.center_x, req.center_y, req.center_z,
            req.size_x, req.size_y, req.size_z,
            req.exhaustiveness, req.num_modes,
        )

        # Immediately create a "running" record so the job list / polling can see it
        try:
            from database.models import DockingJob as DBDockingJob
            running_entry = DBDockingJob(
                id=job_id,
                name=req.ligand_name or f"Docking {job_id[:8]}",
                receptor_name=req.receptor_name,
                ligand_name=req.ligand_name,
                grid={
                    "center": {"x": req.center_x, "y": req.center_y, "z": req.center_z},
                    "size":   {"x": req.size_x,   "y": req.size_y,   "z": req.size_z},
                    "exhaustiveness": req.exhaustiveness,
                    "num_modes": req.num_modes,
                },
                status="running",
                workspace_path=DockingWorkspaceService.get_workspace(job_id),
            )
            db.add(running_entry)
            db.commit()
        except Exception as db_err:
            logger.warning("Could not create running DockingJob record for %s (non-fatal): %s", job_id, db_err)

        # Prepare payload for the background task (avoid passing the full Pydantic object)
        payload = {
            "protein_pdbqt": req.protein_pdbqt,
            "ligand_pdbqt": req.ligand_pdbqt,
            "center_x": req.center_x,
            "center_y": req.center_y,
            "center_z": req.center_z,
            "size_x": req.size_x,
            "size_y": req.size_y,
            "size_z": req.size_z,
            "exhaustiveness": req.exhaustiveness,
            "num_modes": req.num_modes,
            "scoring_function": req.scoring_function,
            "seed": req.seed,
            "selected_chains": req.selected_chains,
            "protein_analysis_summary": req.protein_analysis_summary,
            "receptor_name": req.receptor_name,
            "ligand_name": req.ligand_name,
        }

        # Queue the real work — this is the key fix for the "stuck" UI
        background_tasks.add_task(
            _run_docking_in_background,
            job_id,
            payload
        )

        # Return immediately — frontend will poll for completion
        return {
            "job_id": job_id,
            "status": "running",
            "message": "Docking job started in background. Poll /api/docking/job/{job_id} for the report."
        }

    except Exception as e:
        raise HTTPException(500, f"Failed to start docking job: {e}")


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


# ── Redocking Validation (Advanced Docking P1) ──────────────────────

@router.post("/receptor/redock_validate")
async def redock_validate(req: RedockValidateRequest):
    """Re-dock the receptor's co-crystal ligand and report RMSD to the crystal pose."""
    _require_docking()
    try:
        return DockingWorkspaceService.redock_validation(
            req.pdb_text, resname=req.resname, chain=req.chain, resnum=req.resnum,
            exhaustiveness=req.exhaustiveness, num_modes=req.num_modes,
            scoring_function=req.scoring_function, seed=req.seed,
            remove_water=req.remove_water,
        )
    except Exception as e:
        raise HTTPException(400, f"Redocking validation failed: {e}")


# ── Advanced Ligand Preparation (Advanced Docking P2) ────────────────

@router.post("/ligand/prepare")
async def ligand_prepare(req: LigandPrepRequest):
    """Prepare one or more docking-ready ligand states (Meeko-first, enumeration opt-in)."""
    _require_docking()
    try:
        options = {
            "ph": req.ph,
            "enumerate_protonation": req.enumerate_protonation,
            "enumerate_tautomers": req.enumerate_tautomers,
            "enumerate_stereo": req.enumerate_stereo,
            "n_conformers": req.n_conformers,
            "prefer_meeko": req.prefer_meeko,
        }
        states = DockingWorkspaceService.prepare_ligand_states(req.smiles, options)
        return {"states": states, "count": len(states)}
    except Exception as e:
        raise HTTPException(400, f"Ligand preparation failed: {e}")


# ── Pose Rescoring / Consensus (Advanced Docking P5) ─────────────────

@router.post("/pose/rescore")
async def rescore_pose(req: RescoreRequest):
    """Re-score a stored pose with a second scoring function (consensus)."""
    _require_docking()
    try:
        return DockingWorkspaceService.rescore_pose(
            req.job_id, rank=req.rank, scoring_function=req.scoring_function
        )
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(400, f"Rescoring failed: {e}")


# ── Batch / Ensemble Docking (Advanced Docking P4) ───────────────────

def _run_batch_in_background(batch_id: str, req_dict: dict):
    """Execute a batch docking run in the background and persist batch_report.json."""
    try:
        DockingWorkspaceService.run_batch_docking(
            receptor_pdbqt=req_dict["protein_pdbqt"],
            ligands=req_dict["ligands"],
            center_x=req_dict["center_x"], center_y=req_dict["center_y"], center_z=req_dict["center_z"],
            size_x=req_dict["size_x"], size_y=req_dict["size_y"], size_z=req_dict["size_z"],
            exhaustiveness=req_dict.get("exhaustiveness", 8),
            num_modes=req_dict.get("num_modes", 9),
            scoring_function=req_dict.get("scoring_function", "vina"),
            seed=req_dict.get("seed"),
            ligand_prep_options=req_dict.get("ligand_prep_options"),
            reference_interactions=req_dict.get("reference_interactions"),
            batch_id=batch_id,
        )
    except Exception as exc:
        logger.exception("Background batch docking %s failed: %s", batch_id, exc)


@router.post("/batch_run")
async def batch_run(req: BatchRunRequest, background_tasks: BackgroundTasks):
    """Dock a set of ligands against one receptor+grid. Returns a batch_id to poll."""
    _require_docking()
    try:
        import uuid as _uuid
        batch_id = str(_uuid.uuid4())
        payload = {
            "protein_pdbqt": req.protein_pdbqt,
            "ligands": [{"smiles": l.smiles, "name": l.name} for l in req.ligands],
            "center_x": req.center_x, "center_y": req.center_y, "center_z": req.center_z,
            "size_x": req.size_x, "size_y": req.size_y, "size_z": req.size_z,
            "exhaustiveness": req.exhaustiveness, "num_modes": req.num_modes,
            "scoring_function": req.scoring_function, "seed": req.seed,
            "ligand_prep_options": req.ligand_prep_options,
            "reference_interactions": req.reference_interactions,
        }
        background_tasks.add_task(_run_batch_in_background, batch_id, payload)
        return {
            "batch_id": batch_id,
            "status": "running",
            "num_ligands": len(req.ligands),
            "message": "Batch docking started. Poll GET /api/docking/batch/{batch_id} for the report.",
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to start batch docking: {e}")


@router.get("/batch/{batch_id}")
async def get_batch(batch_id: str):
    """Return the batch docking report (404 while still running)."""
    _require_docking()
    try:
        return DockingWorkspaceService.get_batch_report(batch_id)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(400, f"Failed to load batch report: {e}")


# ── New for Phase 1: Load full job for Pose Analysis page ─────────

@router.get("/job/{job_id}")
async def get_job(job_id: str, db: Session = Depends(get_db)):
    """Return the full docking report + DB metadata for a job."""
    _require_docking()
    try:
        try:
            report = DockingWorkspaceService.get_job_report(job_id)
        except FileNotFoundError:
            report = None  # still running / not yet written; allow pollers to continue
        db_record = DockingWorkspaceService().get_docking_job(db, job_id)
        if report is None and db_record is None:
            raise FileNotFoundError(f"No docking job {job_id}")
        return {
            "job_id": job_id,
            "report": report,
            "db_record": db_record,
        }
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(400, f"Failed to load docking job: {e}")


@router.get("/jobs")
async def list_docking_jobs(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List recent docking jobs (from DB)."""
    try:
        service = DockingWorkspaceService()
        items = service.list_docking_jobs(db, limit=limit, offset=offset)
        return {"items": items, "count": len(items)}
    except Exception as e:
        raise HTTPException(400, f"Failed to list docking jobs: {e}")


# ── ChimeraX Integration Endpoints (first slice) ─────────────────────

class ChimeraRequest(BaseModel):
    rank: int = 1

class ReceptorChimeraRequest(BaseModel):
    pdb_text: str


@router.post("/receptor/launch_chimera")
async def launch_chimera_receptor(req: ReceptorChimeraRequest):
    """
    Saves the provided PDB text to a temporary file and uses the OS default
    handler (e.g. ChimeraX) to open it.
    """
    _require_docking()
    import tempfile
    import os
    import sys
    import subprocess
    try:
        fd, path = tempfile.mkstemp(suffix=".pdb", prefix="receptor_preview_")
        with os.fdopen(fd, 'w') as f:
            f.write(req.pdb_text)
        
        if os.name == 'nt':
            os.startfile(path)
        else:
            opener = 'open' if sys.platform == 'darwin' else 'xdg-open'
            subprocess.Popen([opener, path])
            
        return {"success": True, "message": "Launched external viewer."}
    except Exception as e:
        raise HTTPException(400, f"Failed to launch external viewer: {e}")


@router.post("/job/{job_id}/chimera_script")
async def get_chimera_script(job_id: str, req: ChimeraRequest):
    """Return a high-quality ChimeraX .cxc script for the given pose."""
    _require_docking()
    try:
        service = DockingWorkspaceService()
        script = service.get_chimera_script(job_id, rank=req.rank)
        return {
            "job_id": job_id,
            "rank": req.rank,
            "script": script,
            "filename": f"view_pose_{req.rank}.cxc"
        }
    except Exception as e:
        raise HTTPException(400, f"Failed to generate ChimeraX script: {e}")


@router.post("/job/{job_id}/chimera_bundle")
async def create_chimera_bundle_endpoint(job_id: str, req: ChimeraRequest):
    """
    Create a self-contained folder with .cxc script + structure files.
    Returns the path on the server (the frontend can offer to download or open it).
    """
    _require_docking()
    try:
        service = DockingWorkspaceService()
        bundle_path = service.create_chimera_bundle(job_id, rank=req.rank)
        return {
            "job_id": job_id,
            "rank": req.rank,
            "bundle_path": bundle_path,
            "message": "Bundle created successfully. You can open the .cxc file from this folder in ChimeraX."
        }
    except Exception as e:
        raise HTTPException(400, f"Failed to create ChimeraX bundle: {e}")


@router.post("/job/{job_id}/launch_chimera")
async def launch_chimera(job_id: str, req: ChimeraRequest):
    """
    Best-effort launch of ChimeraX with the visualization script for a pose.
    Requires the executable to be configured in Settings.
    """
    _require_docking()
    try:
        service = DockingWorkspaceService()
        result = service.launch_chimera(job_id, rank=req.rank)
        if result.get("success"):
            return result
        else:
            raise HTTPException(400, result.get("error", "Launch failed"))
    except Exception as e:
        raise HTTPException(400, f"Failed to launch ChimeraX: {e}")


# ── Pre-docking Protein Analysis (Advanced Docking Phase 1) ─────────────

@router.post("/protein_analyze", response_model=ProteinAnalysisResult if ProteinAnalysisResult else None)
async def protein_analyze(req: ProteinAnalyzeRequest):
    """
    Legacy endpoint (fully supported for backward compatibility).
    Returns the original simpler analysis format.
    """
    _require_docking()
    if ProteinAnalyzeRequest is None:
        raise HTTPException(500, "Docking schemas failed to load")

    try:
        analysis = DockingWorkspaceService.analyze_protein(req.pdb_text)
        return analysis
    except Exception as e:
        raise HTTPException(400, f"Protein analysis failed: {e}")


@router.post("/protein/analyze")
async def protein_analyze_rich(req: ProteinAnalyzeRequest):
    """Rich protein analysis endpoint returning the full receptor report."""
    _require_docking()
    if ProteinAnalyzeRequest is None:
        raise HTTPException(500, "Docking schemas failed to load")

    try:
        report = DockingWorkspaceService.analyze_receptor(req.pdb_text)
        return report
    except Exception as e:
        raise HTTPException(400, f"Protein analysis failed: {e}")


@router.post("/protein/chains", response_model=ProteinChainsResult if ProteinChainsResult else None)
async def protein_chain_summary(req: ProteinAnalyzeRequest):
    """Return per-chain counts, hetero classification, and dock recommendation."""
    _require_docking()
    if ProteinChainsResult is None:
        raise HTTPException(500, "Docking schemas failed to load")

    try:
        report = DockingWorkspaceService.analyze_receptor(req.pdb_text)
        chains = []
        for chain in report.get("chains", []) if isinstance(report, dict) else []:
            ligand_names = [l["resname"] for l in report.get("ligands", []) if l["chain_id"] == chain["chain_id"]]
            cofactor_names = [c["resname"] for c in report.get("cofactors", []) if c["chain_id"] == chain["chain_id"]]
            metal_elements = [m["element"] for m in report.get("metals", []) if m["chain_id"] == chain["chain_id"]]
            chains.append({
                "chain_id": chain["chain_id"],
                "num_residues": chain.get("num_residues", 0),
                "num_standard_aa": chain.get("num_standard_aa", 0),
                "num_hetero": chain.get("num_hetero", 0),
                "num_waters": chain.get("num_waters", 0),
                "hetero_names": chain.get("hetero_names", []),
                "ligands": ligand_names,
                "cofactors": cofactor_names,
                "metals": metal_elements,
                "missing_residues": [mr for mr in report.get("missing_residues", []) if mr.get("chain_id") == chain["chain_id"]],
            })
        return {
            "chains": chains,
            "total_chains": report.get("total_chains", len(chains)),
            "recommendation": report.get("recommendation", {}),
        }
    except Exception as e:
        raise HTTPException(400, f"Chain summary failed: {e}")


@router.post("/protein/waters", response_model=ProteinWatersResult if ProteinWatersResult else None)
async def protein_waters(req: ProteinAnalyzeRequest):
    """Return water classification and keep/remove recommendations."""
    _require_docking()
    if ProteinWatersResult is None:
        raise HTTPException(500, "Docking schemas failed to load")

    try:
        result = DockingWorkspaceService.classify_waters(req.pdb_text)
        return result
    except Exception as e:
        raise HTTPException(400, f"Water analysis failed: {e}")


@router.post("/protein/cofactors", response_model=ProteinCofactorsResult if ProteinCofactorsResult else None)
async def protein_cofactors(req: ProteinAnalyzeRequest):
    """Return detected cofactors with required/optional/artifact classification."""
    _require_docking()
    if ProteinCofactorsResult is None:
        raise HTTPException(500, "Docking schemas failed to load")

    try:
        report = DockingWorkspaceService.analyze_receptor(req.pdb_text)
        cofactors = report.get("cofactors", []) if isinstance(report, dict) else []
        return {
            "cofactors": cofactors,
            "total": len(cofactors)
        }
    except Exception as e:
        raise HTTPException(400, f"Cofactor analysis failed: {e}")


@router.post("/protein/metals", response_model=ProteinMetalsResult if ProteinMetalsResult else None)
async def protein_metals(req: ProteinAnalyzeRequest):
    """Return detected metals with coordinating residues and catalytic relevance."""
    _require_docking()
    if ProteinMetalsResult is None:
        raise HTTPException(500, "Docking schemas failed to load")

    try:
        report = DockingWorkspaceService.analyze_receptor(req.pdb_text)
        metals = report.get("metals", []) if isinstance(report, dict) else []
        return {
            "metals": metals,
            "total": len(metals)
        }
    except Exception as e:
        raise HTTPException(400, f"Metal analysis failed: {e}")


@router.post("/protein/quality", response_model=ProteinQualityResult if ProteinQualityResult else None)
async def protein_quality(req: ProteinAnalyzeRequest):
    """Return receptor quality score and breakdown."""
    _require_docking()
    if ProteinQualityResult is None:
        raise HTTPException(500, "Docking schemas failed to load")

    try:
        result = DockingWorkspaceService.get_quality_assessment(req.pdb_text)
        return result
    except Exception as e:
        raise HTTPException(400, f"Quality assessment failed: {e}")


@router.post("/receptor/analyze")
async def receptor_analyze(req: ProteinAnalyzeRequest):
    """
    NEW recommended endpoint for rich receptor analysis (Phase 1+).

    Returns the significantly richer ReceptorReport with:
    - Proper ligand / cofactor / metal classification
    - Resolution and experimental method (when available)
    - Quality score (0-100) + label
    - Better foundation for active site detection and preparation decisions

    New frontend code and serious docking studies should prefer this endpoint.
    """
    _require_docking()
    try:
        pdb_text = _resolve_structure_text(req.pdb_text, req.asset_id)
        report = DockingWorkspaceService.analyze_receptor(pdb_text)
        return report
    except Exception as e:
        raise HTTPException(400, f"Receptor analysis failed: {e}")


@router.post("/receptor/ligand_sites")
async def detect_ligand_binding_sites(req: ProteinAnalyzeRequest):
    """
    Phase 3A: Returns ligand-derived binding site suggestions with
    recommended grid boxes when co-crystallized ligands are present.
    """
    _require_docking()
    try:
        sites = DockingWorkspaceService.detect_ligand_binding_sites(req.pdb_text)
        return {"sites": sites, "count": len(sites)}
    except Exception as e:
        raise HTTPException(400, f"Ligand site detection failed: {e}")


@router.post("/receptor/pockets")
async def detect_pockets(req: ProteinAnalyzeRequest):
    """
    Phase 3B: Pocket detection using fpocket (when no co-crystallized ligand is present).
    Returns predicted pockets with suggested grid boxes.
    """
    _require_docking()
    try:
        result = DockingWorkspaceService.detect_pockets(req.pdb_text)
        return result
    except Exception as e:
        raise HTTPException(400, f"Pocket detection failed: {e}")


@router.post("/receptor/waters")
async def classify_waters(req: ProteinAnalyzeRequest):
    """
    Phase 6: Classify waters into active-site vs bulk and return
    Keep/Remove recommendations based on proximity to binding sites.
    """
    _require_docking()
    try:
        result = DockingWorkspaceService.classify_waters(req.pdb_text)
        return result
    except Exception as e:
        raise HTTPException(400, f"Water classification failed: {e}")


@router.post("/receptor/protonate")
async def protonate_receptor(req: ProteinAnalyzeRequest):
    """
    Phase 7: Standalone protonation of a receptor at a given pH
    using PDB2PQR + PropKa (if available).
    """
    _require_docking()
    ph = 7.4  # Could be extended to accept ph in request later
    try:
        protonated = DockingWorkspaceService.protonate_receptor(req.pdb_text, ph=ph)
        return {"pdb": protonated, "ph": ph}
    except Exception as e:
        raise HTTPException(400, f"Protonation failed: {e}")


@router.post("/receptor/quality")
async def get_quality_assessment(req: ProteinAnalyzeRequest):
    """
    Phase 8: Returns a detailed quality assessment (0-100) for the receptor,
    including breakdown of contributing factors.
    """
    _require_docking()
    try:
        result = DockingWorkspaceService.get_quality_assessment(req.pdb_text)
        return result
    except Exception as e:
        raise HTTPException(400, f"Quality assessment failed: {e}")


class AIChainRecommendationRequest(BaseModel):
    """Request for AI expert chain recommendation."""
    analysis: Dict[str, Any]                    # full ProteinAnalysis dict from /protein_analyze
    ligand_smiles: Optional[str] = None
    target_name: Optional[str] = None


class AIExpertRequest(BaseModel):
    question: str
    pdb_text: Optional[str] = None
    analysis: Optional[Dict[str, Any]] = None
    domain: Optional[str] = "general"
    provider: Optional[str] = None


class AIExpertDomainRequest(BaseModel):
    pdb_text: str
    analysis: Optional[Dict[str, Any]] = None


def _recommendation_to_dict(rec):
    return {
        "recommendation": rec.recommendation,
        "confidence": rec.confidence,
        "reasoning": rec.reasoning,
        "provider_used": rec.provider_used,
        "metadata": rec.metadata,
    }


@router.post("/ai_expert")
async def ai_expert(req: AIExpertRequest):
    _require_docking()
    try:
        result = ask_expert(
            question=req.question,
            pdb_text=req.pdb_text,
            analysis_dict=req.analysis,
            domain=req.domain,
            provider=req.provider,
        )
        return _recommendation_to_dict(result)
    except Exception as e:
        raise HTTPException(400, f"AI expert query failed: {e}")


@router.post("/ai_expert/pocket")
async def ai_expert_pocket(req: AIExpertDomainRequest):
    _require_docking()
    try:
        result = recommend_pocket(req.pdb_text, req.analysis)
        return _recommendation_to_dict(result)
    except Exception as e:
        raise HTTPException(400, f"AI pocket recommendation failed: {e}")


@router.post("/ai_expert/waters")
async def ai_expert_waters(req: AIExpertDomainRequest):
    _require_docking()
    try:
        result = recommend_waters(req.pdb_text, req.analysis)
        return _recommendation_to_dict(result)
    except Exception as e:
        raise HTTPException(400, f"AI water recommendation failed: {e}")


@router.post("/ai_expert/cofactors")
async def ai_expert_cofactors(req: AIExpertDomainRequest):
    _require_docking()
    try:
        result = recommend_cofactors(req.pdb_text, req.analysis)
        return _recommendation_to_dict(result)
    except Exception as e:
        raise HTTPException(400, f"AI cofactor recommendation failed: {e}")


@router.post("/ai_expert/metals")
async def ai_expert_metals(req: AIExpertDomainRequest):
    _require_docking()
    try:
        result = recommend_metals(req.pdb_text, req.analysis)
        return _recommendation_to_dict(result)
    except Exception as e:
        raise HTTPException(400, f"AI metal recommendation failed: {e}")


@router.post("/ai_expert/chain")
async def ai_expert_chain(req: AIChainRecommendationRequest):
    return await ai_chain_recommendation(req)


@router.post("/ai_chain_recommendation")
async def ai_chain_recommendation(req: AIChainRecommendationRequest):
    """
    Ask the 25-year expert docking AI for the best chain(s) to dock against.

    This is the high-value "AI kicks in for real multi-chain targets" feature.
    It returns a structured recommendation with rich scientific rationale.
    """
    _require_docking()
    try:
        service = DockingWorkspaceService()
        result = service.get_ai_chain_recommendation(
            analysis_dict=req.analysis,
            ligand_smiles=req.ligand_smiles,
            target_name=req.target_name,
        )
        return result
    except Exception as e:
        raise HTTPException(400, f"AI chain recommendation failed: {e}")
