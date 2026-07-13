from fastapi import APIRouter, Depends, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from database.models import get_db
from database.models import OptimizationCampaign, Portfolio, CampaignSeriesLink, SeriesCompound, OptimizationDecision
from services.campaign_service import CampaignService
from services.ai.lead_opt_expert import LeadOptExpertService
import json
from pathlib import Path

try:
    from api.routes import _page_ctx
except ImportError:
    def _page_ctx(request, **kwargs):
        return {"request": request, **kwargs}

templates = Jinja2Templates(directory=str(Path("templates").absolute()))
router = APIRouter()
expert_service = LeadOptExpertService()

@router.get("/", response_class=HTMLResponse)
async def lead_opt_studio_page(request: Request, db: Session = Depends(get_db)):
    campaigns = db.query(OptimizationCampaign).order_by(OptimizationCampaign.created_at.desc()).all()
    return templates.TemplateResponse(request, "lead_opt_studio.html", _page_ctx(request, campaigns=campaigns))

@router.get("/portfolios", response_class=JSONResponse)
async def list_portfolios(project_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Portfolios, scoped to a project when project_id is supplied."""
    svc = CampaignService(db)
    if project_id:
        ports = svc.portfolios_for_project(project_id)
    else:
        ports = db.query(Portfolio).order_by(Portfolio.created_at.desc()).all()
    return [{"id": p.id, "name": p.name, "project_id": p.project_id} for p in ports]

@router.get("/campaigns", response_class=JSONResponse)
async def list_campaigns(project_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Campaigns, scoped via Project -> Portfolio -> Campaign when project_id is supplied."""
    svc = CampaignService(db)
    if project_id:
        camps = svc.campaigns_for_project(project_id)
    else:
        camps = db.query(OptimizationCampaign).order_by(OptimizationCampaign.created_at.desc()).all()
    return [{"id": c.id, "name": c.name, "goal_type": c.goal_type} for c in camps]

@router.get("/series", response_class=JSONResponse)
async def list_project_series(project_id: str, db: Session = Depends(get_db)):
    """The project's reachable series set (via its campaigns)."""
    svc = CampaignService(db)
    return [{"id": s.id, "name": s.name, "target_name": s.target_name} for s in svc.series_for_project(project_id)]

@router.get("/campaign/{campaign_id}/compounds", response_class=JSONResponse)
async def list_campaign_compounds(campaign_id: str, db: Session = Depends(get_db)):
    """
    Compounds reachable from a campaign (Campaign -> Series -> Compounds).
    Backs the What-If compound selector so the user never types a cmp_ id.
    """
    series_ids = [l.series_id for l in db.query(CampaignSeriesLink).filter_by(campaign_id=campaign_id).all()]
    if not series_ids:
        return []
    compounds = (
        db.query(SeriesCompound)
        .filter(SeriesCompound.series_id.in_(series_ids))
        .order_by(SeriesCompound.name.asc())
        .all()
    )
    return [
        {"id": c.id, "name": c.name, "smiles": c.smiles, "pic50": c.normalized_value}
        for c in compounds
    ]

@router.post("/portfolio", response_class=JSONResponse)
async def create_portfolio(
    name: str = Form(...),
    description: str = Form(""),
    project_id: str = Form(""),
    db: Session = Depends(get_db)
):
    """Create a Portfolio, owned by a ResearchProject when project_id is supplied."""
    svc = CampaignService(db)
    try:
        p = svc.create_portfolio(name, description, project_id or None)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": p.id, "name": p.name, "project_id": p.project_id}

@router.post("/campaign", response_class=JSONResponse)
async def create_campaign(
    name: str = Form(...),
    portfolio_id: str = Form(...),
    goal_type: str = Form("generic"),
    series_id: str = Form(""),
    db: Session = Depends(get_db)
):
    """Create an OptimizationCampaign under a portfolio, optionally linking a series."""
    svc = CampaignService(db)
    try:
        camp = svc.create_campaign(portfolio_id, name, goal_type, {})
        if series_id:
            svc.link_series_to_campaign(camp.id, series_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": camp.id, "name": camp.name, "goal_type": camp.goal_type}

@router.get("/campaign/{campaign_id}/dashboard", response_class=HTMLResponse)
async def get_campaign_dashboard(campaign_id: str, db: Session = Depends(get_db)):
    campaign = db.query(OptimizationCampaign).filter_by(id=campaign_id).first()
    if not campaign:
        return HTMLResponse("<div class='text-red-500'>Campaign not found.</div>")
        
    svc = CampaignService(db)
    
    # Get all linked series
    links = db.query(CampaignSeriesLink).filter_by(campaign_id=campaign_id).all()
    series_ids = [l.series_id for l in links]
    
    compounds = db.query(SeriesCompound).filter(SeriesCompound.series_id.in_(series_ids)).all()
    
    # Calculate MPO scores and prepare data
    scored_compounds = []
    plot_data = []
    
    for c in compounds:
        mpo = svc.calculate_compound_mpo(c, campaign_id)
        scored_compounds.append({"compound": c, "mpo": mpo})
        
        # For plot: x = pIC50, y = Generic MPO, r = MW/50
        pic50 = c.normalized_value or 0
        mw = c.properties.get("mw", 300) if c.properties else 300
        plot_data.append({
            "x": pic50,
            "y": mpo["generic"],
            "r": mw / 50,
            "name": c.name,
            "id": c.id
        })
        
    # Sort by Generic MPO descending
    scored_compounds.sort(key=lambda x: x["mpo"]["generic"], reverse=True)
    
    plot_json = json.dumps(plot_data)
    
    html = f"""
    <div class='mb-6 bg-white p-4 rounded-lg border border-slate-200 shadow-sm'>
        <div class='flex justify-between items-center mb-4'>
            <h3 class='font-bold text-slate-800'>Design Space Explorer</h3>
            <span class='text-xs text-slate-500'>X: pIC50 | Y: Generic MPO Score | Size: MW</span>
        </div>
        <div class='w-full h-64'>
            <canvas id='mpo-scatter-chart' data-points='{plot_json}'></canvas>
        </div>
    </div>
    
    <div class='mb-4 flex justify-between items-center'>
        <h3 class='font-bold text-slate-800'>Lead Prioritization</h3>
        <button hx-post='/api/lead-opt/campaign/{campaign_id}/ai-prioritize' hx-target='#ai-priority-res' class='text-xs bg-indigo-600 text-white hover:bg-indigo-700 font-bold px-3 py-1.5 rounded'>
            AI Tradeoff Analysis
        </button>
    </div>
    
    <div id='ai-priority-res' class='mb-6'></div>
    
    <div class='overflow-x-auto bg-white rounded-lg border border-slate-200 shadow-sm'>
        <table class='w-full text-left text-sm'>
            <thead class='bg-slate-50 text-slate-600 uppercase text-[10px] font-bold'>
                <tr>
                    <th class='px-4 py-3'>Rank</th>
                    <th class='px-4 py-3'>Compound</th>
                    <th class='px-4 py-3'>Status</th>
                    <th class='px-4 py-3 text-right'>pIC50</th>
                    <th class='px-4 py-3 text-right'>Generic MPO</th>
                    <th class='px-4 py-3 text-right'>Pfizer CNS MPO</th>
                    <th class='px-4 py-3'>Actions</th>
                </tr>
            </thead>
            <tbody class='divide-y divide-slate-200'>
    """
    
    for idx, sc in enumerate(scored_compounds[:50]): # Top 50
        c = sc["compound"]
        mpo = sc["mpo"]
        status = c.properties.get("candidate_status", "Hit") if c.properties else "Hit"
        
        status_color = "bg-slate-100 text-slate-700"
        if status == "Lead": status_color = "bg-emerald-100 text-emerald-800"
        elif status == "Discarded": status_color = "bg-rose-100 text-rose-800"
        elif status == "Backup Lead": status_color = "bg-blue-100 text-blue-800"
        
        html += f"""
        <tr class='hover:bg-slate-50 transition-colors'>
            <td class='px-4 py-3 font-mono text-xs text-slate-500'>#{idx+1}</td>
            <td class='px-4 py-3 font-bold text-slate-800'>{c.name}</td>
            <td class='px-4 py-3'><span class='text-[10px] uppercase font-bold px-2 py-1 rounded {status_color}'>{status}</span></td>
            <td class='px-4 py-3 text-right font-mono text-xs'>{c.normalized_value or '--'}</td>
            <td class='px-4 py-3 text-right font-mono text-xs font-bold text-indigo-600'>{mpo['generic']}</td>
            <td class='px-4 py-3 text-right font-mono text-xs text-slate-600'>{mpo['pfizer_cns']}</td>
            <td class='px-4 py-3'>
                <button onclick='openDecisionModal("{c.id}", "{c.name}")' class='text-xs text-indigo-600 hover:text-indigo-800 font-semibold'>Log Decision</button>
            </td>
        </tr>
        """
        
    html += "</tbody></table></div>"
    
    # Decisions Ledger
    decisions = db.query(OptimizationDecision).filter_by(campaign_id=campaign_id).order_by(OptimizationDecision.date.desc()).limit(10).all()
    if decisions:
        html += "<div class='mt-8'><h3 class='font-bold text-slate-800 mb-4'>Recent Decisions Ledger</h3><div class='space-y-3'>"
        for d in decisions:
            color = "border-slate-200"
            if d.decision_type == "Lead": color = "border-emerald-300 bg-emerald-50"
            elif d.decision_type == "Discarded": color = "border-rose-300 bg-rose-50"
            
            html += f"""
            <div class='border rounded p-3 text-sm {color}'>
                <div class='flex justify-between items-center mb-1'>
                    <span class='font-bold text-slate-800 uppercase text-[10px] tracking-wide'>{d.decision_type}</span>
                    <span class='text-slate-400 text-xs'>{d.date.strftime('%Y-%m-%d %H:%M')}</span>
                </div>
                <p class='text-slate-700'>{d.rationale}</p>
            </div>
            """
        html += "</div></div>"
    
    return HTMLResponse(html)

@router.post("/campaign/{campaign_id}/ai-prioritize", response_class=HTMLResponse)
async def ai_prioritize(campaign_id: str, db: Session = Depends(get_db)):
    campaign = db.query(OptimizationCampaign).filter_by(id=campaign_id).first()
    svc = CampaignService(db)
    
    links = db.query(CampaignSeriesLink).filter_by(campaign_id=campaign_id).all()
    series_ids = [l.series_id for l in links]
    compounds = db.query(SeriesCompound).filter(SeriesCompound.series_id.in_(series_ids)).all()
    
    # Prepare top 10 for AI
    scored = []
    for c in compounds:
        scored.append({
            "name": c.name,
            "mpo": svc.calculate_compound_mpo(c, campaign_id),
            "alerts": [a['name'] for a in c.properties.get('admet', {}).get('alerts', [])] if c.properties else []
        })
    scored.sort(key=lambda x: x["mpo"]["generic"], reverse=True)
    
    report = expert_service.prioritize_leads(campaign.name, scored[:10])
    return HTMLResponse(f"<div class='prose prose-sm prose-indigo max-w-none bg-indigo-50 p-4 rounded border border-indigo-100'>{report}</div>")

@router.post("/campaign/{campaign_id}/decision", response_class=JSONResponse)
async def log_decision(
    campaign_id: str,
    compound_id: str = Form(...),
    decision_type: str = Form(...),
    rationale: str = Form(...),
    db: Session = Depends(get_db)
):
    svc = CampaignService(db)
    svc.record_decision(campaign_id, [compound_id], decision_type, rationale)
    return {"status": "success"}

@router.post("/compound/{compound_id}/what-if", response_class=HTMLResponse)
async def ai_what_if(compound_id: str, hypothesis: str = Form(...), db: Session = Depends(get_db)):
    c = db.query(SeriesCompound).filter_by(id=compound_id).first()
    if not c:
        return HTMLResponse("Compound not found.")
        
    compound_data = {
        "name": c.name,
        "properties": c.properties,
        "pic50": c.normalized_value
    }
    
    report = expert_service.what_if_analysis(compound_data, hypothesis)
    return HTMLResponse(f"<div class='prose prose-sm prose-indigo max-w-none'>{report}</div>")
