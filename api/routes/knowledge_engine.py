from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database.models import get_db
from database.models import KnowledgeRule, RuleContradiction
from services.knowledge_miner import KnowledgeMinerService
from services.ai.scientific_librarian import ScientificLibrarianService
from pathlib import Path

try:
    from api.routes import _page_ctx
except ImportError:
    def _page_ctx(request, **kwargs):
        return {"request": request, **kwargs}

templates = Jinja2Templates(directory=str(Path("templates").absolute()))
router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def knowledge_dashboard(request: Request, db: Session = Depends(get_db)):
    rules = db.query(KnowledgeRule).all()
    contradictions = db.query(RuleContradiction).filter_by(status="Unresolved").all()
    return templates.TemplateResponse(request, "knowledge_engine.html", _page_ctx(request, rules=rules, contradictions=contradictions))

@router.post("/mine", response_class=HTMLResponse)
async def trigger_mining(
    request: Request,
    project_id: str = Form(""),
    db: Session = Depends(get_db),
):
    """
    Mines recurring failure modes. Cross-project by default (that is the point
    of the Knowledge Engine); pass project_id to explicitly scope to one project.
    """
    svc = KnowledgeMinerService(db)
    count = svc.mine_cross_project_patterns(project_id or None)

    project = None
    if project_id:
        from database.models import ResearchProject
        project = db.query(ResearchProject).filter_by(id=project_id).first()

    rules = db.query(KnowledgeRule).order_by(KnowledgeRule.created_at.desc()).all()
    contradictions = db.query(RuleContradiction).filter_by(status="Unresolved").all()

    scope = f"within {project.name}" if project else "across all projects"
    msg = (
        f"<div class='bg-emerald-100 text-emerald-800 p-2 rounded mb-4 text-sm font-bold'>"
        f"Mining complete ({scope})! Found {count} new patterns.</div>"
    )
    html = templates.TemplateResponse(
        request,
        "knowledge_engine.html",
        _page_ctx(request, project=project, rules=rules, contradictions=contradictions),
    ).body.decode()

    # Simple injection for HTMX response without building full components
    return HTMLResponse(msg + html)

@router.post("/ask", response_class=HTMLResponse)
async def ask_librarian(query: str = Form(...), db: Session = Depends(get_db)):
    svc = ScientificLibrarianService(db)
    raw_md = svc.ask_question(query)
    
    # Simple HTML conversion to avoid requiring the 'markdown' pip package
    html_content = raw_md.replace("\\n", "<br>").replace("**", "<b>")
    # Clean up trailing <b> tags if odd number
    if html_content.count("<b>") % 2 != 0:
        html_content = html_content[::-1].replace("<b>", "</b>", 1)[::-1]
    html_content = html_content.replace("<b>", "<strong>").replace("</b>", "</strong>")

    return HTMLResponse(f"<div class='prose prose-sm prose-slate max-w-none'>{html_content}</div>")

@router.post("/rule/{rule_id}/approve", response_class=HTMLResponse)
async def approve_rule(rule_id: str, db: Session = Depends(get_db)):
    rule = db.query(KnowledgeRule).filter_by(id=rule_id).first()
    if rule:
        rule.status = "Approved"
        db.commit()
    return HTMLResponse("<span class='text-emerald-600 font-bold'>Approved</span>")

@router.post("/rule/{rule_id}/reject", response_class=HTMLResponse)
async def reject_rule(rule_id: str, db: Session = Depends(get_db)):
    rule = db.query(KnowledgeRule).filter_by(id=rule_id).first()
    if rule:
        rule.status = "Rejected"
        db.commit()
    return HTMLResponse("<span class='text-red-600 font-bold'>Rejected</span>")
