from fastapi import APIRouter, Depends, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
import json
import logging
import re

from database.models import get_db, ScreeningWorkspace, ScreeningHit, Workspace
from services.screening_service import ScreeningService
from services.clustering_service import cluster_screening_hits
from services.ai.docking_expert import DockingExpertService

logger = logging.getLogger(__name__)

router = APIRouter()
expert_service = DockingExpertService()

# Defense-in-depth sanitizer for AI-generated HTML: the triage report is rendered as
# HTML, so strip anything that could execute or break the page while keeping the
# formatting tags the prompt asks for (headings, lists, emphasis).
_UNSAFE_BLOCK = re.compile(r"<(script|style|iframe|object|embed)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_UNSAFE_TAG = re.compile(r"</?(script|style|iframe|object|embed|link|meta|base|form)\b[^>]*>", re.IGNORECASE)
_EVENT_ATTR = re.compile(r"""\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)""", re.IGNORECASE)
_JS_URI = re.compile(r"""(href|src)\s*=\s*("|')\s*javascript:[^"']*\2""", re.IGNORECASE)
_CODE_FENCE = re.compile(r"^\s*```(?:html)?\s*|\s*```\s*$", re.IGNORECASE)


def _sanitize_report_html(fragment: str) -> str:
    """Remove executable/dangerous markup from an AI-produced HTML fragment."""
    if not fragment:
        return ""
    cleaned = _CODE_FENCE.sub("", fragment.strip())
    cleaned = _UNSAFE_BLOCK.sub("", cleaned)
    cleaned = _UNSAFE_TAG.sub("", cleaned)
    cleaned = _EVENT_ATTR.sub("", cleaned)
    cleaned = _JS_URI.sub(r'\1=\2#\2', cleaned)
    return cleaned.strip()

@router.post("/start")
async def start_screening(
    background_tasks: BackgroundTasks,
    workspace_id: str = Form(...),
    grid_json: str = Form(...),
    library_file: UploadFile = File(...),
    exhaustiveness: int = Form(8),
    db: Session = Depends(get_db)
):
    """Parses library, creates DB rows, and queues the screening job."""
    content = await library_file.read()
    content_str = content.decode('utf-8', errors='ignore')
    
    grid = json.loads(grid_json)
    
    # Needs to verify Workspace exists and has a prepared receptor PDBQT
    from services.workspace_manager import get_workspace

    ws = get_workspace(db, workspace_id)
    if not ws:
        raise HTTPException(status_code=400, detail="Receptor workspace not found.")

    heavy = ws.get("heavy_data") or {}
    receptor_pdbqt = (
        heavy.get("protein_pdbqt")
        or heavy.get("receptor_pdbqt")
        or heavy.get("prepared_receptor")
        or heavy.get("pdbqt")
        or heavy.get("receptor")
    )
    if not receptor_pdbqt or not str(receptor_pdbqt).strip():
        raise HTTPException(
            status_code=400,
            detail="No prepared receptor PDBQT found in workspace. Prepare the receptor before screening.",
        )

    svc = ScreeningService(db)

    try:
        job_id = svc.create_job(workspace_id, grid, content_str, library_file.filename, exhaustiveness)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    background_tasks.add_task(svc.run_screening_job, job_id, str(receptor_pdbqt))

    return {"job_id": job_id, "status": "queued"}

@router.get("/{job_id}/status", response_class=JSONResponse)
async def screening_status(job_id: str, db: Session = Depends(get_db)):
    """Poll endpoint for the frontend dashboard."""
    job = db.query(ScreeningWorkspace).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
        
    return job.to_dict()

@router.post("/{job_id}/promote_top_n", response_class=JSONResponse)
async def promote_top_n(job_id: str, series_id: str = Form(...), n: int = Form(10), db: Session = Depends(get_db)):
    from services.medchem_service import MedchemService
    hits = db.query(ScreeningHit).filter_by(screening_id=job_id).order_by(ScreeningHit.best_affinity.asc()).limit(n).all()
    
    if not hits:
        raise HTTPException(404, "No hits found")
        
    svc = MedchemService(db)
    count = 0
    for hit in hits:
        svc.add_compound_advanced(
            series_id=series_id,
            smiles=hit.smiles,
            name=hit.ligand_name,
            docking_affinity=hit.best_affinity,
            screening_hit_id=hit.id,
            tags=["Top-N Promoted"]
        )
        count += 1
        
    return {"status": "success", "promoted_count": count}

@router.post("/{job_id}/promote_cluster", response_class=JSONResponse)
async def promote_cluster(job_id: str, series_id: str = Form(...), scaffold_smiles: str = Form(...), db: Session = Depends(get_db)):
    from services.medchem_service import MedchemService
    hits = db.query(ScreeningHit).filter_by(screening_id=job_id, scaffold_smiles=scaffold_smiles).all()
    
    if not hits:
        raise HTTPException(404, "No hits found in this cluster")
        
    svc = MedchemService(db)
    count = 0
    for hit in hits:
        svc.add_compound_advanced(
            series_id=series_id,
            smiles=hit.smiles,
            name=hit.ligand_name,
            docking_affinity=hit.best_affinity,
            screening_hit_id=hit.id,
            tags=["Cluster Promoted"]
        )
        count += 1
        
    return {"status": "success", "promoted_count": count}

@router.get("/{job_id}/hits", response_class=HTMLResponse)
async def screening_hits_html(job_id: str, db: Session = Depends(get_db)):
    """Returns HTMX rows for the datatable of top hits."""
    hits = db.query(ScreeningHit).filter_by(screening_id=job_id).order_by(ScreeningHit.affinity_value.asc()).limit(50).all()
    
    if not hits:
        return HTMLResponse("<tr><td colspan='4' class='text-center py-4 text-slate-500'>No completed hits yet.</td></tr>")
        
    html = ""
    for i, hit in enumerate(hits):
        affinity_str = f"{hit.best_affinity} kcal/mol" if hit.best_affinity else "Failed"
        status_color = "emerald" if hit.status == "completed" else ("red" if hit.status == "failed" else "blue")
        
        # Link to the existing pose analysis workspace
        # We reuse the Pose Analysis view directly
        review_url = f"/pose-analysis?job_id={job_id}&hit_id={hit.id}"
        
        html += f"""
        <tr class='border-b border-slate-100 hover:bg-slate-50'>
            <td class='py-3 px-4'>{i+1}</td>
            <td class='py-3 px-4 font-semibold text-slate-900'>{hit.ligand_name}</td>
            <td class='py-3 px-4 font-mono text-xs text-slate-500 truncate max-w-[200px]'>{hit.smiles}</td>
            <td class='py-3 px-4'>
                <span class='px-2 py-1 bg-{status_color}-100 text-{status_color}-700 text-xs font-bold rounded-full'>{affinity_str}</span>
            </td>
            <td class='py-3 px-4 flex items-center gap-3'>
                <a href="{review_url}" class="text-indigo-600 hover:text-indigo-800 text-sm font-semibold">Review Pose &rarr;</a>
                <button type="button" @click="promoteHit('{hit.id}')" class="text-[10px] uppercase font-bold text-slate-500 hover:text-indigo-600 tracking-wider">Promote to Series</button>
            </td>
        </tr>
        """
    return HTMLResponse(html)

@router.post("/{job_id}/triage", response_class=HTMLResponse)
async def ai_triage(job_id: str, db: Session = Depends(get_db)):
    """Cluster the completed hits for this screening job and produce an AI hit-triage
    HTML report. Never raises to the frontend: on any failure it returns a graceful
    HTML message, and the underlying screening results are left untouched."""
    try:
        # Single query — the top completed hits for THIS job only (scoped by
        # screening_id, no N+1: clustering runs in memory on already-loaded rows).
        hits = (
            db.query(ScreeningHit)
            .filter_by(screening_id=job_id, status="completed")
            .order_by(ScreeningHit.affinity_value.asc())
            .limit(10)
            .all()
        )

        if not hits:
            # Nothing to triage — return a friendly message and DO NOT call the AI provider.
            return HTMLResponse(
                "<div class='text-slate-500 text-sm'>No completed hits are available for triage yet.</div>"
            )

        clusters = cluster_screening_hits(hits)

        def _affinity(value):
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        clusters_payload = []
        for scaffold, cluster_hits in clusters.items():
            affinities = [a for a in (_affinity(h.best_affinity) for h in cluster_hits) if a is not None]
            # Representative = the strongest-binding member of the cluster.
            representative = min(
                cluster_hits,
                key=lambda h: (_affinity(h.best_affinity) if _affinity(h.best_affinity) is not None else float("inf")),
            )
            clusters_payload.append({
                "scaffold": scaffold,
                "cluster_size": len(cluster_hits),
                "representative_ligand": representative.ligand_name,
                "representative_smiles": representative.smiles,
                "best_affinity_kcal_mol": min(affinities) if affinities else None,
                "average_affinity_kcal_mol": round(sum(affinities) / len(affinities), 2) if affinities else None,
                "interaction_summary": representative.interactions_summary,
                "pose": representative.pose_path or representative.id,
            })

        prompt = f"""You are a senior computational medicinal chemist performing hit triage for a virtual screening campaign.
The completed docking hits have been clustered by their Murcko scaffold. Each cluster below includes a representative
(strongest-binding) member with its ligand name, SMILES, best and average affinity (kcal/mol), a summary of the
detected protein-ligand interactions, and a pose identifier.

SCAFFOLD CLUSTERS (docking data is ground truth - do not invent interactions or affinities not present):
{json.dumps(clusters_payload, indent=2, default=str)}

Produce a rich, well-structured HTML report FRAGMENT (no <html>, <head>, or <body> tags). Use <h4> section headings,
<p>, <ul>/<li>, and <strong> for emphasis. Include exactly these sections, grounded only in the data above:
  1. Most promising scaffolds - rank the clusters and justify using affinity and interactions.
  2. SAR observations - structure-activity relationships across and within clusters.
  3. Likely binding features - key interactions inferred from the interaction summaries (if none are recorded, say so; do not invent them).
  4. Lead prioritization - which representative compounds to advance first, and why.
  5. Suggested follow-up compounds - concrete analog ideas (described in words, no invented SMILES).
  6. Medicinal chemistry optimization ideas - specific, actionable modifications.
If only a single scaffold cluster is present, still provide a useful report by focusing on within-cluster SAR,
member prioritization, binding features, and optimization ideas. Return ONLY the HTML fragment."""

        # Single AI entry point - AIProviderManager centralizes provider selection + fallback.
        response = expert_service.ai.query(prompt)

        if response.provider_used == "none" or response.error:
            # Provider failed: results are untouched; warn gracefully, never raise.
            logger.warning("AI triage provider unavailable for job %s: %s", job_id, response.error)
            return HTMLResponse(
                "<div class='text-amber-600 text-sm'>AI triage is temporarily unavailable "
                "(no AI provider could be reached). Your screening results are unaffected - please try again shortly.</div>"
            )

        safe_html = _sanitize_report_html(response.text)
        return HTMLResponse(
            f"""<div class="prose prose-sm prose-emerald dark:prose-invert max-w-none">{safe_html}</div>"""
        )

    except Exception as exc:  # never leak an exception/500 to the frontend
        logger.exception("AI triage failed for job %s: %s", job_id, exc)
        return HTMLResponse(
            "<div class='text-amber-600 text-sm'>AI triage could not be completed due to an internal error. "
            "Your screening results are preserved.</div>"
        )
