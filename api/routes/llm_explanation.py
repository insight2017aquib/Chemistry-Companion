from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from llm.explanation_models import DockingExplanationRequest, PoseExplanationRequest, DockingExplanationResponse
from llm.docking_explainer import explain_docking_result, explain_single_pose
from llm import HAS_LLM

router = APIRouter()

@router.post("/explain_docking", response_model=DockingExplanationResponse)
async def explain_docking(req: DockingExplanationRequest):
    if not HAS_LLM:
        return DockingExplanationResponse(explanation="LLM explanation unavailable (configure OPENROUTER_API_KEY).")
        
    try:
        exp = explain_docking_result(req.poses, req.interactions, req.smiles)
        return DockingExplanationResponse(explanation=exp)
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/explain_pose", response_model=DockingExplanationResponse)
async def explain_pose(req: PoseExplanationRequest):
    if not HAS_LLM:
        return DockingExplanationResponse(explanation="LLM explanation unavailable (configure OPENROUTER_API_KEY).")
        
    try:
        exp = explain_single_pose(req.pose, req.interactions, req.smiles)
        return DockingExplanationResponse(explanation=exp)
    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/explain_pose_htmx", response_class=HTMLResponse)
async def explain_pose_htmx(
    request: Request,
    smiles: str = Form(""),
    pose_rank: int = Form(1),
    affinity: float = Form(0.0)
):
    if not HAS_LLM:
        return HTMLResponse(
            '<div class="p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded border border-red-200 dark:border-red-800">'
            '<strong>LLM Unavailable:</strong> Please configure OPENROUTER_API_KEY in your .env file.'
            '</div>'
        )
        
    try:
        pose = {"rank": pose_rank, "affinity": affinity}
        interactions = [{"type": "H-bond", "protein_residue": "Unknown", "ligand_atom": "Unknown", "distance": 0.0}] # mock for HTMX demo
        exp = explain_single_pose(pose, interactions, smiles)
        return HTMLResponse(f'<div class="prose prose-sm prose-indigo dark:prose-invert max-w-none text-slate-700 dark:text-slate-300 whitespace-pre-wrap">{exp}</div>')
    except Exception as e:
        return HTMLResponse(
            f'<div class="p-4 bg-red-50 text-red-600 rounded border border-red-200">Error generating explanation: {str(e)}</div>'
        )
