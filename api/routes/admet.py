from fastapi import APIRouter, Depends, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database.models import get_db
from database.models import ChemicalSeries, SeriesCompound
from services.ai.developability_expert import DevelopabilityExpertService
import json
from pathlib import Path

# Fix templates path depending on execution directory
try:
    from api.routes import _page_ctx
except ImportError:
    def _page_ctx(request, **kwargs):
        return {"request": request, **kwargs}

templates = Jinja2Templates(directory=str(Path("templates").absolute()))

router = APIRouter()
expert_service = DevelopabilityExpertService()

@router.get("/", response_class=HTMLResponse)
async def admet_workbench_page(request: Request, db: Session = Depends(get_db)):
    series = db.query(ChemicalSeries).order_by(ChemicalSeries.updated_at.desc()).all()
    return templates.TemplateResponse(request, "admet_workbench.html", _page_ctx(request, series=series))

@router.get("/series/{series_id}/dashboard", response_class=HTMLResponse)
async def get_admet_dashboard(series_id: str, db: Session = Depends(get_db)):
    """Returns the HTMX fragment for the ADMET Traffic Light Dashboard and Radar Charts."""
    series = db.query(ChemicalSeries).filter_by(id=series_id).first()
    if not series:
        return HTMLResponse("<div class='text-red-500'>Series not found.</div>")
        
    compounds = db.query(SeriesCompound).filter_by(series_id=series_id).all()
    if not compounds:
        return HTMLResponse("<div class='text-slate-500 p-4 text-center'>No compounds in this series to analyze.</div>")
        
    html = "<div class='grid grid-cols-1 gap-6'>"
    
    for c in compounds:
        props = c.properties or {}
        admet = props.get('admet', {})
        alerts = admet.get('alerts', [])
        
        # Color coding for traffic lights
        def color_risk(risk_val):
            val = str(risk_val).lower()
            if 'high' in val: return "bg-red-100 text-red-800 border-red-200"
            if 'moderate' in val or 'fair' in val: return "bg-yellow-100 text-yellow-800 border-yellow-200"
            return "bg-emerald-100 text-emerald-800 border-emerald-200"

        # Radar chart data payload
        radar_data = {
            "mw": props.get('mw', 0),
            "logp": props.get('logp', 0),
            "tpsa": props.get('tpsa', 0),
            "hbd": props.get('hbd', 0) * 100, # scaled for visual
            "hba": props.get('hba', 0) * 50   # scaled for visual
        }
        radar_json = json.dumps(radar_data)
            
        html += f"""
        <div class='bg-white p-5 rounded-lg border border-slate-200 shadow-sm flex flex-col md:flex-row gap-6 items-start'>
            <div class='flex-1 w-full'>
                <div class='flex justify-between items-center mb-3'>
                    <h3 class='font-bold text-slate-800'>{c.name}</h3>
                    <div class='text-xs font-bold px-2 py-1 rounded {color_risk(admet.get('developability_rank', 'Poor'))}'>
                        Score: {admet.get('developability_score', 'N/A')} ({admet.get('developability_rank', 'N/A')})
                    </div>
                </div>
                
                <div class='grid grid-cols-2 lg:grid-cols-4 gap-3 text-xs mb-4'>
                    <div class='border rounded p-2 {color_risk(admet.get("solubility", {}).get("risk", ""))}'>
                        <div class='font-bold opacity-75 uppercase text-[9px]'>Solubility</div>
                        <div class='font-semibold'>{admet.get('solubility', {}).get('risk', '--')}</div>
                    </div>
                    <div class='border rounded p-2 {color_risk(admet.get("permeability", {}).get("risk", ""))}'>
                        <div class='font-bold opacity-75 uppercase text-[9px]'>Permeability</div>
                        <div class='font-semibold'>{admet.get('permeability', {}).get('risk', '--')}</div>
                    </div>
                    <div class='border rounded p-2 {color_risk(admet.get("bbb", {}).get("risk", ""))}'>
                        <div class='font-bold opacity-75 uppercase text-[9px]'>BBB</div>
                        <div class='font-semibold'>{admet.get('bbb', {}).get('risk', '--')}</div>
                    </div>
                    <div class='border rounded p-2 {color_risk(admet.get("herg", {}).get("risk", ""))}'>
                        <div class='font-bold opacity-75 uppercase text-[9px]'>hERG Risk</div>
                        <div class='font-semibold'>{admet.get('herg', {}).get('risk', '--')}</div>
                    </div>
                </div>
                
                """
        if alerts:
            html += "<div class='mb-4'><div class='text-[10px] uppercase font-bold text-slate-500 mb-1'>Structural Alerts</div><div class='flex flex-wrap gap-2'>"
            for alert in alerts:
                html += f"<span class='bg-rose-100 text-rose-700 border border-rose-200 text-xs px-2 py-1 rounded' title='{alert['description']}'>{alert['type']}: {alert['name']}</span>"
            html += "</div></div>"
            
        html += f"""
                <div class='mt-4'>
                    <button hx-post='/api/admet/compound/{c.id}/ai-explain' hx-target='#ai-res-{c.id}' class='text-xs bg-indigo-50 text-indigo-700 hover:bg-indigo-100 font-bold px-3 py-1.5 rounded border border-indigo-200'>
                        AI Optimization Analysis
                    </button>
                    <div id='ai-res-{c.id}' class='mt-3 text-sm'></div>
                </div>
            </div>
            
            <div class='w-full md:w-64 h-64 shrink-0'>
                <canvas class='radar-chart-canvas' data-stats='{radar_json}'></canvas>
            </div>
        </div>
        """
        
    html += "</div>"
    return HTMLResponse(html)

@router.post("/series/{series_id}/ai-analyze", response_class=HTMLResponse)
async def ai_analyze_series(series_id: str, db: Session = Depends(get_db)):
    series = db.query(ChemicalSeries).filter_by(id=series_id).first()
    compounds = db.query(SeriesCompound).filter_by(series_id=series_id).all()
    
    summary_data = []
    for c in compounds:
        summary_data.append({
            "name": c.name,
            "developability_score": c.properties.get('admet', {}).get('developability_score'),
            "alerts": [a['name'] for a in c.properties.get('admet', {}).get('alerts', [])]
        })
        
    report = expert_service.analyze_series_liabilities(series.name, summary_data)
    return HTMLResponse(f"<div class='prose prose-sm prose-indigo max-w-none'>{report}</div>")

@router.post("/compound/{compound_id}/ai-explain", response_class=HTMLResponse)
async def ai_explain_compound(compound_id: str, db: Session = Depends(get_db)):
    c = db.query(SeriesCompound).filter_by(id=compound_id).first()
    if not c:
        return HTMLResponse("Compound not found.")
        
    report = expert_service.suggest_optimization_targets(c.properties)
    return HTMLResponse(f"<div class='prose prose-sm prose-indigo max-w-none bg-slate-50 p-4 rounded border border-slate-100'>{report}</div>")
