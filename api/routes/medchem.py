from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import json

from database.models import get_db, ScreeningHit
from services.medchem_service import MedchemService, calculate_properties
from services.bioisostere_service import suggest_replacements
from services.ai.medchem_expert import MedChemExpertService
from services.import_service import ImportService
from services.mmp_service import MMPEngine
from services.report_service import ReportService

router = APIRouter()
expert_service = MedChemExpertService()

@router.get("/series", response_class=JSONResponse)
async def list_series(db: Session = Depends(get_db)):
    svc = MedchemService(db)
    return svc.list_series()

@router.post("/series", response_class=JSONResponse)
async def create_series(name: str = Form(...), target: str = Form(...), notes: str = Form(""), db: Session = Depends(get_db)):
    svc = MedchemService(db)
    series = svc.create_series(name, target, notes)
    return series.to_dict()

@router.get("/series/{series_id}/compounds", response_class=HTMLResponse)
async def get_series_compounds_html(series_id: str, db: Session = Depends(get_db)):
    svc = MedchemService(db)
    compounds = svc.get_compounds(series_id)
    
    if not compounds:
        return HTMLResponse("<tr><td colspan='10' class='text-center py-4 text-slate-500'>No compounds in this series yet.</td></tr>")
        
    html = ""
    for i, c in enumerate(compounds):
        props = c.get("properties", {})
        sa_cat = props.get("sa_category", "Unknown")
        sa_score = props.get("sa_score", "N/A")
        
        sa_color = "slate"
        if sa_cat == "High": sa_color = "emerald"
        elif sa_cat == "Moderate": sa_color = "amber"
        elif sa_cat == "Low": sa_color = "red"
        
        pic50 = c.get("normalized_value")
        if pic50 is None:
            pic50 = "--"
        affinity = c.get("docking_affinity", "--")
        
        # Lipinski & Veber flags
        flags = ""
        if not props.get("lipinski_pass"): flags += "<span title='Lipinski Violations > 1' class='text-red-500 font-bold'>[L]</span> "
        if not props.get("veber_pass"): flags += "<span title='Veber Violations' class='text-orange-500 font-bold'>[V]</span>"
        
        html += f"""
        <tr class='border-b border-slate-100 hover:bg-slate-50' data-id='{c['id']}' data-smiles='{c['smiles']}'>
            <td class='py-2 px-3'>{i+1}</td>
            <td class='py-2 px-3 font-semibold text-slate-900'>{c['name']} {flags}</td>
            <td class='py-2 px-3 font-mono text-[10px] text-slate-500 truncate max-w-[120px]' title='{c['smiles']}'>{c['smiles']}</td>
            <td class='py-2 px-3 font-bold text-indigo-600'>{pic50}</td>
            <td class='py-2 px-3 font-bold text-slate-600'>{affinity}</td>
            <td class='py-2 px-3'>{props.get('mw', '--')}</td>
            <td class='py-2 px-3'>{props.get('logp', '--')}</td>
            <td class='py-2 px-3'>{props.get('tpsa', '--')}</td>
            <td class='py-2 px-3 text-xs'>
                <div class='flex flex-col'>
                    <span class='font-bold text-{sa_color}-600'>{sa_cat}</span>
                    <span class='text-[10px] text-slate-400'>Score: {sa_score}</span>
                </div>
            </td>
            <td class='py-2 px-3'>
                <button type="button" @click="designAnalogs('{c['id']}')" class="text-xs text-indigo-600 hover:text-indigo-800 font-semibold bg-indigo-50 px-2 py-1 rounded border border-indigo-200">Design</button>
            </td>
        </tr>
        """
    return HTMLResponse(html)

@router.get("/series/{series_id}/sar-data", response_class=JSONResponse)
async def get_series_sar_data(series_id: str, db: Session = Depends(get_db)):
    """
    Returns real SAR plot points (LogP vs pIC50) for the series so the
    frontend bubble chart can render actual compound data instead of a stub.
    Compounds missing LogP or a normalized activity value are skipped.
    """
    svc = MedchemService(db)
    compounds = svc.get_compounds(series_id)

    points = []
    for c in compounds:
        props = c.get("properties") or {}
        logp = props.get("logp")
        pic50 = c.get("normalized_value")
        if logp is None or pic50 is None:
            continue

        # Bubble radius scaled from molecular weight (fallback to a fixed size).
        mw = props.get("mw")
        radius = 10
        if isinstance(mw, (int, float)):
            radius = max(5, min(20, mw / 40.0))

        points.append({
            "id": c.get("id"),
            "name": c.get("name"),
            "x": logp,
            "y": pic50,
            "r": round(radius, 1),
        })

    return {"points": points}

@router.post("/series/{series_id}/compounds", response_class=JSONResponse)
async def add_compound(
    series_id: str, 
    smiles: str = Form(...), 
    name: str = Form(...), 
    pic50: Optional[float] = Form(None),
    ic50: Optional[float] = Form(None),
    docking_affinity: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    svc = MedchemService(db)
    c = svc.add_compound(series_id, smiles, name, ic50=ic50, pic50=pic50, docking_affinity=docking_affinity)
    return c.to_dict()

@router.post("/series/promote_hit", response_class=JSONResponse)
async def promote_hit(hit_id: str = Form(...), series_id: str = Form(...), db: Session = Depends(get_db)):
    hit = db.query(ScreeningHit).filter_by(id=hit_id).first()
    if not hit:
        raise HTTPException(404, "Hit not found")
        
    svc = MedchemService(db)
    c = svc.add_compound(
        series_id=series_id,
        smiles=hit.smiles,
        name=hit.ligand_name,
        docking_affinity=hit.best_affinity,
        screening_hit_id=hit.id
    )
    return {"status": "success", "compound": c.to_dict()}

@router.post("/compounds/{compound_id}/bioisosteres", response_class=HTMLResponse)
async def get_bioisosteres(compound_id: str, db: Session = Depends(get_db)):
    from database.models import SeriesCompound
    c = db.query(SeriesCompound).filter_by(id=compound_id).first()
    if not c:
        return HTMLResponse("<div class='text-red-500'>Compound not found.</div>")
        
    replacements = suggest_replacements(c.smiles)
    
    if not replacements:
        return HTMLResponse("<div class='text-slate-500 text-sm'>No curated bioisostere rules matched this compound.</div>")
        
    html = f"<div class='space-y-4'><h4 class='font-bold text-slate-800'>Rule-Based Bioisostere Suggestions for {c.name}</h4>"
    for r in replacements:
        html += f"""
        <div class='border border-blue-200 bg-blue-50 rounded p-3'>
            <div class='font-semibold text-blue-900 mb-2'>Target Group: {r['target_group']}</div>
            <ul class='space-y-2 text-sm'>
        """
        for rep in r['replacements']:
            html += f"""
                <li class='bg-white p-2 rounded border border-blue-100 flex flex-col'>
                    <span class='font-bold text-slate-800'>{rep['name']} <span class='font-mono text-xs text-slate-500 font-normal ml-2'>{rep['smiles']}</span></span>
                    <span class='text-slate-600 text-xs mt-1'>{rep['rationale']}</span>
                </li>
            """
        html += "</ul></div>"
    html += "</div>"
    
    return HTMLResponse(html)

@router.post("/series/{series_id}/ai-sar", response_class=HTMLResponse)
async def ai_sar_analysis(series_id: str, db: Session = Depends(get_db)):
    svc = MedchemService(db)
    series = svc.get_series(series_id)
    compounds = svc.get_compounds(series_id)
    
    if not compounds:
        return HTMLResponse("<div class='text-slate-500'>Add compounds to generate SAR.</div>")
        
    try:
        report = expert_service.analyze_sar_trends(series.name, compounds)
        html = f"<div class='prose prose-sm prose-indigo max-w-none'>{report}</div>"
        return HTMLResponse(html)
    except Exception as e:
        return HTMLResponse(f"<div class='text-red-500'>AI analysis failed: {str(e)}</div>")

@router.post("/compounds/{compound_id}/ai-design", response_class=HTMLResponse)
async def ai_analog_design(compound_id: str, target_profile: str = Form(...), db: Session = Depends(get_db)):
    from database.models import SeriesCompound
    c = db.query(SeriesCompound).filter_by(id=compound_id).first()
    if not c:
        return HTMLResponse("<div class='text-red-500'>Compound not found.</div>")
        
    try:
        report = expert_service.suggest_analogs(c.to_dict(), target_profile)
        html = f"<div class='prose prose-sm prose-purple max-w-none mt-4'>{report}</div>"
        return HTMLResponse(html)
    except Exception as e:
        return HTMLResponse(f"<div class='text-red-500'>AI design failed: {str(e)}</div>")

from fastapi import UploadFile, File

@router.post("/series/{series_id}/import", response_class=JSONResponse)
async def import_dataset(
    series_id: str, 
    file: UploadFile = File(...),
    column_map: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        col_map = json.loads(column_map)
        svc = MedchemService(db)
        importer = ImportService(db, svc)
        
        file_bytes = await file.read()
        res = importer.import_dataset(series_id, file_bytes, file.filename, col_map)
        return res
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/series/{series_id}/mmps", response_class=HTMLResponse)
async def get_series_mmps(series_id: str, db: Session = Depends(get_db)):
    engine = MMPEngine(db)
    mmps = engine.find_mmps(series_id)
    
    if not mmps:
        return HTMLResponse("<div class='text-slate-500 text-sm'>No Matched Molecular Pairs found in this series.</div>")
        
    html = "<ul class='space-y-3'>"
    for m in mmps:
        html += f"""
        <li class='bg-white border rounded p-3 text-sm'>
            <div class='flex justify-between items-center mb-1'>
                <span class='font-bold text-slate-800'>{m['cmpd1_name']} vs {m['cmpd2_name']}</span>
                <span class='bg-indigo-100 text-indigo-800 text-[10px] font-bold px-2 py-1 rounded'>{m['transformation']}</span>
            </div>
            <div class='flex gap-4 text-xs text-slate-600'>
                <span>&Delta; pIC50: <span class='font-bold {'text-emerald-600' if m['delta_pic50'] and m['delta_pic50'] > 0 else 'text-red-600'}'>{m['delta_pic50']}</span></span>
                <span>&Delta; LogP: <span class='font-bold'>{m['delta_logp']}</span></span>
            </div>
        </li>
        """
    html += "</ul>"
    return HTMLResponse(html)

@router.get("/series/{series_id}/report")
async def get_series_report(series_id: str, db: Session = Depends(get_db)):
    svc = ReportService(db)
    md = svc.generate_series_report(series_id)
    return HTMLResponse(f"<pre class='whitespace-pre-wrap font-sans text-sm'>{md}</pre>")
