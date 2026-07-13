from fastapi import APIRouter, Depends, HTTPException, Form, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database.models import get_db
from database.models import ResearchProject, OptimizationCampaign, CampaignSeriesLink, SeriesCompound
from services.publication_service import PublicationService, DOCX_AVAILABLE
from services.ai.scientific_writer import ScientificWriterService
import json
from pathlib import Path

try:
    from api.routes import _page_ctx
except ImportError:
    def _page_ctx(request, **kwargs):
        return {"request": request, **kwargs}

templates = Jinja2Templates(directory=str(Path("templates").absolute()))
router = APIRouter()
writer_service = ScientificWriterService()

@router.get("/", response_class=HTMLResponse)
async def publication_studio_page(request: Request, db: Session = Depends(get_db)):
    projects = db.query(ResearchProject).all()
    campaigns = db.query(OptimizationCampaign).all()
    return templates.TemplateResponse(request, "publication_studio.html", _page_ctx(request, projects=projects, campaigns=campaigns, docx_available=DOCX_AVAILABLE))

@router.get("/table/campaign/{campaign_id}", response_class=Response)
async def download_table(campaign_id: str, format: str = "csv", db: Session = Depends(get_db)):
    svc = PublicationService(db)

    campaign = db.query(OptimizationCampaign).filter_by(id=campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    try:
        content = svc.generate_compound_table(campaign_id, format_type=format)
    except ImportError as e:
        # e.g. DOCX requested without python-docx installed
        raise HTTPException(status_code=400, detail=str(e))

    if not content:
        raise HTTPException(status_code=400, detail="Invalid format or no data.")

    filename = f"campaign_{campaign.name.replace(' ', '_')}_table"

    # Persist the exported table so a manuscript can cite it later.
    project_id = svc.project_id_for_campaign(campaign_id)
    if project_id:
        ws = svc.get_or_create_workspace(project_id)
        svc.save_table_asset(
            workspace_id=ws.id,
            title=f"Compound Table — {campaign.name}",
            table_type="Compound SAR",
            payload={
                "campaign_id": campaign_id,
                "format": format,
                "csv": svc.generate_compound_table(campaign_id, format_type="csv"),
            },
            caption=f"SAR and ADMET summary for campaign {campaign.name}.",
        )

    if format == "csv":
        return Response(content=content, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}.csv"})
    elif format == "latex":
        return Response(content=content, media_type="text/plain", headers={"Content-Disposition": f"attachment; filename={filename}.tex"})
    elif format == "docx":
        return Response(content=content, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers={"Content-Disposition": f"attachment; filename={filename}.docx"})
    else:
        raise HTTPException(status_code=400, detail="Unsupported format.")

@router.get("/citations/project/{project_id}", response_class=HTMLResponse)
async def get_citations(project_id: str, style: str = "ACS", db: Session = Depends(get_db)):
    svc = PublicationService(db)
    citations = svc.format_citations(project_id, style)
    
    if not citations:
        return HTMLResponse("<div class='text-slate-500 text-sm'>No literature references found for this project.</div>")
        
    html = f"<div class='space-y-3 font-serif text-sm'>"
    for c in citations:
        html += f"<div class='pl-4 -indent-4 leading-relaxed'>{c['text']}</div>"
    html += "</div>"
    
    return HTMLResponse(html)

@router.post("/ai/draft-results", response_class=JSONResponse)
async def draft_results(campaign_id: str = Form(...), db: Session = Depends(get_db)):
    campaign = db.query(OptimizationCampaign).filter_by(id=campaign_id).first()
    if not campaign:
        return JSONResponse({"error": "Campaign not found."}, status_code=404)

    links = db.query(CampaignSeriesLink).filter_by(campaign_id=campaign_id).all()
    series_ids = [l.series_id for l in links]
    compounds = db.query(SeriesCompound).filter(SeriesCompound.series_id.in_(series_ids)).all()

    # Sort and take top 5 for results writeup
    compounds.sort(key=lambda x: x.normalized_value or 0, reverse=True)
    c_data = [{"id": c.id, "name": c.name, "pIC50": c.normalized_value, "LogP": (c.properties or {}).get("logp")} for c in compounds[:5]]

    draft = writer_service.draft_results_section(campaign.name, c_data)
    draft_html = f"<div class='prose prose-sm prose-slate max-w-none'>{draft}</div>"

    svc = PublicationService(db)

    # Persist the draft against its project, together with an evidence map that
    # points at the real entities the text was generated from. Resolves the
    # canonical path Campaign -> Portfolio -> Project.
    draft_id = None
    version = None
    project_id = svc.project_id_for_campaign(campaign_id)
    if project_id:
        evidence_map = {
            "campaign_id": campaign_id,
            "series_ids": series_ids,
            "compounds": c_data,
        }
        ws = svc.get_or_create_workspace(project_id)
        saved = svc.save_draft(
            workspace_id=ws.id,
            title=f"Results — {campaign.name}",
            content_type="Results",
            content=draft_html,
            evidence=evidence_map,
        )
        draft_id, version = saved.id, saved.version

    # The traceability panel is populated from the *real* compounds the draft
    # was based on (their actual IDs and properties), not a hardcoded stub.
    return JSONResponse({
        "draft_html": draft_html,
        "evidence": c_data,
        "draft_id": draft_id,
        "version": version,
        "persisted": draft_id is not None,
    })


@router.get("/project/{project_id}/drafts", response_class=JSONResponse)
async def list_drafts(project_id: str, db: Session = Depends(get_db)):
    """Persisted drafts for a project, each with its evidence map."""
    svc = PublicationService(db)
    return [
        {
            "id": d.id,
            "title": d.title,
            "content_type": d.content_type,
            "version": d.version,
            "status": d.status,
            "evidence_links": d.evidence_links or {},
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in svc.list_drafts(project_id)
    ]
    
@router.post("/ai/draft-caption", response_class=HTMLResponse)
async def draft_caption(figure_type: str = Form(...), context: str = Form(...), db: Session = Depends(get_db)):
    caption = writer_service.generate_figure_caption(figure_type, context)
    return HTMLResponse(f"<div class='bg-slate-100 p-3 rounded text-sm italic font-serif border border-slate-200'>{caption}</div>")
