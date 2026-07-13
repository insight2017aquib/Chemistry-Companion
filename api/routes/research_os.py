from fastapi import APIRouter, Depends, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database.models import get_db
from database.models import ResearchProject, NotebookEntry, LiteratureReference
from services.project_service import ProjectService
from services.knowledge_graph import KnowledgeGraphService
from services.report_engine import ReportEngineService
from services.ai.research_assistant import ResearchAssistantService
import json
from pathlib import Path

try:
    from api.routes import _page_ctx
except ImportError:
    def _page_ctx(request, **kwargs):
        return {"request": request, **kwargs}

templates = Jinja2Templates(directory=str(Path("templates").absolute()))
router = APIRouter()
ai_service = ResearchAssistantService()

@router.get("/", response_class=HTMLResponse)
async def research_os_dashboard(request: Request, db: Session = Depends(get_db)):
    projects = db.query(ResearchProject).order_by(ResearchProject.created_at.desc()).all()
    return templates.TemplateResponse(request, "research_os.html", _page_ctx(request, projects=projects))

@router.post("/project", response_class=JSONResponse)
async def create_project(
    name: str = Form(...),
    target: str = Form(""),
    objectives: str = Form(""),
    db: Session = Depends(get_db)
):
    """Create a Research Project (root entity for notebooks, literature, and graph)."""
    svc = ProjectService(db)
    p = svc.create_project(name, target, objectives)
    return {"id": p.id, "name": p.name, "status": p.status}

@router.get("/projects", response_class=JSONResponse)
async def list_projects(db: Session = Depends(get_db)):
    """All research projects (root entities) — used by the project picker."""
    projects = db.query(ResearchProject).order_by(ResearchProject.created_at.desc()).all()
    return [{"id": p.id, "name": p.name, "target": p.target, "status": p.status} for p in projects]

@router.post("/project/{project_id}/portfolio", response_class=JSONResponse)
async def create_project_portfolio(
    project_id: str,
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    """Create a Portfolio owned by this ResearchProject (Project -> Portfolio, 1:N)."""
    from services.campaign_service import CampaignService
    svc = CampaignService(db)
    try:
        p = svc.create_portfolio(name, description, project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"id": p.id, "name": p.name, "project_id": p.project_id}

@router.get("/project/{project_id}/timeline", response_class=HTMLResponse)
async def get_project_timeline(project_id: str, db: Session = Depends(get_db)):
    kg = KnowledgeGraphService(db)
    events = kg.get_timeline(project_id)
    
    if not events:
        return HTMLResponse("<div class='text-slate-500 text-sm text-center p-4'>No scientific events recorded yet.</div>")
        
    html = "<div class='space-y-4 border-l-2 border-slate-200 ml-3 pl-4'>"
    for e in events:
        # Determine color/icon based on type
        bg = "bg-slate-100"
        border = "border-slate-200"
        icon = "📝"
        
        t = str(e['type']).lower()
        if "decision" in t:
            bg = "bg-indigo-50"
            border = "border-indigo-200"
            icon = "⚖️"
        elif "hypothesis" in t:
            bg = "bg-amber-50"
            border = "border-amber-200"
            icon = "💡"
        elif "conclusion" in t:
            bg = "bg-emerald-50"
            border = "border-emerald-200"
            icon = "✅"
            
        date_str = e['date'].strftime('%Y-%m-%d %H:%M')
            
        html += f"""
        <div class='relative'>
            <div class='absolute -left-[25px] bg-white rounded-full border-2 {border} w-6 h-6 flex items-center justify-center text-[10px]'>{icon}</div>
            <div class='{bg} border {border} rounded p-3 text-sm shadow-sm'>
                <div class='flex justify-between items-center mb-1'>
                    <span class='font-bold text-slate-800 text-xs'>{e['type']}</span>
                    <span class='text-slate-400 text-[10px]'>{date_str} | {e['entity']}</span>
                </div>
                <p class='text-slate-700 whitespace-pre-wrap'>{e['content']}</p>
            </div>
        </div>
        """
    html += "</div>"
    return HTMLResponse(html)

@router.get("/project/{project_id}/graph", response_class=JSONResponse)
async def get_knowledge_graph(project_id: str, db: Session = Depends(get_db)):
    kg = KnowledgeGraphService(db)
    return kg.build_project_graph(project_id)

@router.post("/project/{project_id}/notebook", response_class=HTMLResponse)
async def add_notebook_entry(
    project_id: str, 
    entry_type: str = Form(...),
    content: str = Form(...),
    entity_type: str = Form("Project"),
    entity_id: str = Form(""),
    db: Session = Depends(get_db)
):
    svc = ProjectService(db)
    svc.add_notebook_entry(project_id, entity_type, entity_id or project_id, entry_type, content)
    # Return HTMX trigger to refresh timeline
    return HTMLResponse(
        "<div class='text-emerald-600 text-sm font-bold'>Entry saved!</div>"
        "<script>htmx.trigger('body', 'refreshTimeline');</script>"
    )

@router.post("/project/{project_id}/literature", response_class=HTMLResponse)
async def add_literature(
    project_id: str,
    doi: str = Form(...),
    notes: str = Form(""),
    db: Session = Depends(get_db)
):
    svc = ProjectService(db)
    lit = svc.add_literature(project_id, doi, notes)
    return HTMLResponse(f"""
        <div class='border border-slate-200 rounded p-2 text-sm bg-white shadow-sm mb-2'>
            <div class='font-bold text-indigo-700'>{lit.title}</div>
            <div class='text-xs text-slate-500 mb-1'>{lit.authors} ({lit.year}) - {lit.journal}</div>
            <div class='text-xs text-slate-400 font-mono'>DOI: {lit.doi}</div>
        </div>
    """)

@router.post("/project/{project_id}/ai-summarize", response_class=HTMLResponse)
async def ai_summarize_project(project_id: str, db: Session = Depends(get_db)):
    kg = KnowledgeGraphService(db)
    events = kg.get_timeline(project_id)
    project = db.query(ResearchProject).filter_by(id=project_id).first()
    
    if not events:
        return HTMLResponse("<p class='text-slate-500'>Not enough data to summarize.</p>")
        
    report = ai_service.summarize_project(project.name, events)
    return HTMLResponse(f"<div class='prose prose-sm prose-slate max-w-none'>{report}</div>")

@router.post("/project/{project_id}/ai-lessons", response_class=HTMLResponse)
async def ai_lessons_learned(project_id: str, db: Session = Depends(get_db)):
    kg = KnowledgeGraphService(db)
    events = kg.get_timeline(project_id)
    project = db.query(ResearchProject).filter_by(id=project_id).first()
    
    report = ai_service.extract_lessons_learned(project.name, events)
    return HTMLResponse(f"<div class='prose prose-sm prose-slate max-w-none'>{report}</div>")

@router.get("/report/campaign/{campaign_id}/thesis", response_class=HTMLResponse)
async def get_thesis_report(campaign_id: str, format: str = "html", db: Session = Depends(get_db)):
    re = ReportEngineService(db)
    content = re.generate_thesis_tables(campaign_id, format)
    if format == "markdown":
        return HTMLResponse(f"<pre class='text-xs font-mono bg-slate-50 p-4 rounded overflow-x-auto'>{content}</pre>")
    return HTMLResponse(f"<div class='overflow-x-auto'>{content}</div>")
