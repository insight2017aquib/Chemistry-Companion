"""
api/app.py — Chemistry Companion web application
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from api.templating import create_templates
from api.project_context import get_current_project
from core.paths import database_url, outputs_dir, package_root, static_dir, templates_dir
from database.models import configure_database, get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT = package_root()
templates = create_templates(templates_dir())

EXAMPLES = [
    {"name": "Benzene", "smiles": "c1ccccc1"},
    {"name": "Caffeine", "smiles": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"},
    {"name": "Aspirin", "smiles": "CC(=O)Oc1ccccc1C(=O)O"},
    {"name": "Quinoxaline", "smiles": "c1cc2cccnc2nc1"},
]

EXPORT_PROFILES = [
    {"name": "Full Report", "desc": "All descriptor and spectral sheets", "sheets": "Summary, Descriptors, FG, IR, NMR, Metadata"},
    {"name": "Medicinal Chemistry", "desc": "Drug-discovery focused", "sheets": "Summary, Descriptors, FG"},
    {"name": "Spectroscopy", "desc": "IR and NMR focused", "sheets": "Summary, IR, ¹H, ¹³C"},
    {"name": "Teaching", "desc": "Simplified for education", "sheets": "Summary, Descriptors, IR, ¹H"},
    {"name": "Minimal", "desc": "Summary + descriptors only", "sheets": "Summary, Descriptors"},
]


def _page_ctx(request: Request, **extra):
    return {"request": request, "examples": EXAMPLES, **extra}


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_url = database_url()
    configure_database(db_url)
    logger.info("Chemistry Companion started (db=%s)", db_url)
    yield


app = FastAPI(title="Chemistry Companion", version="3.0.0", lifespan=lifespan)

_static = static_dir()
if _static.exists():
    app.mount("/static", StaticFiles(directory=str(_static)), name="static")

_outputs = outputs_dir()
# Create outputs when missing so the /outputs mount is always available
# (portable builds and fresh checkouts).
try:
    _outputs.mkdir(parents=True, exist_ok=True)
except OSError:
    pass
if _outputs.exists():
    app.mount("/outputs", StaticFiles(directory=str(_outputs)), name="outputs")

from .routes import analysis, batch, export, history, spectra, structure  # noqa: E402

app.include_router(analysis.router, prefix="/api", tags=["analysis"])
app.include_router(spectra.router, prefix="/api", tags=["spectra"])
app.include_router(batch.router, prefix="/api", tags=["batch"])
app.include_router(export.router, prefix="/api", tags=["export"])
app.include_router(history.router, prefix="/api", tags=["history"])
app.include_router(structure.router, prefix="/api", tags=["structure"])

from .routes import docking, validation, benchmarks
app.include_router(docking.router, prefix="/api", tags=["docking"])
app.include_router(validation.router, prefix="/api", tags=["validation"])
app.include_router(benchmarks.router, prefix="/api", tags=["benchmarks"])

# ==========================================
# Advanced Features (Phase 2 Additions)
# ==========================================
# Register the newly created isolated routers for Visualization and Docking.
from .routes import visualization as viz_routes
from services.visualization_service import VisualizationService
from .routes import docking_workspace as dock_ws_routes

# Visualization API: handles protein parsing, ligand 2D/3D generation, and overlay rendering
app.include_router(viz_routes.router, prefix="/api/visualization", tags=["visualization"])

# Docking Workspace API: handles protein prep, gridbox detection, Vina execution, and pose extraction
app.include_router(dock_ws_routes.router, prefix="/api/docking", tags=["docking-workspace"])

# Protein Asset Management System (PAMS): fetch/upload/list/view protein structures
# as first-class assets (source-agnostic; reused by viewer + docking).
from .routes import proteins as proteins_routes
app.include_router(proteins_routes.router, prefix="/api/proteins", tags=["proteins"])

# LLM API: provides AI-powered pose explanation (degrades gracefully if API key is missing)
from .routes import llm_explanation as llm_routes
app.include_router(llm_routes.router, prefix="/api/llm", tags=["llm"])

# External Tools (ChimeraX, etc.)
from .routes import external_tools as external_tools_routes
app.include_router(external_tools_routes.router, prefix="/api/external-tools", tags=["external-tools"])

# Workspaces (Phase 1 Persistence)
from .routes import workspace as workspace_routes
app.include_router(workspace_routes.router)

# Virtual Screening (Phase 8)
from .routes import virtual_screening as virtual_screening_routes
app.include_router(virtual_screening_routes.router, prefix="/api/screening", tags=["screening"])

# Medicinal Chemistry Workbench (Phase 9)
from .routes import medchem as medchem_routes
app.include_router(medchem_routes.router, prefix="/api/medchem", tags=["medchem"])

# ADMET & Developability (Phase 10)
from .routes import admet as admet_routes
app.include_router(admet_routes.router, prefix="/api/admet", tags=["admet"])

# Lead Optimization Studio (Phase 11)
from .routes import lead_opt as lead_opt_routes
app.include_router(lead_opt_routes.router, prefix="/api/lead-opt", tags=["lead-opt"])

# Research Operating System (Phase 12)
from .routes import research_os as research_os_routes
app.include_router(research_os_routes.router, prefix="/api/research-os", tags=["research-os"])

# Publication & Thesis Assistant (Phase 13)
from .routes import publication as publication_routes
app.include_router(publication_routes.router, prefix="/api/publication", tags=["publication"])

# Scientific Knowledge Engine (Phase 14)
from .routes import knowledge_engine as knowledge_engine_routes
app.include_router(knowledge_engine_routes.router, prefix="/api/knowledge", tags=["knowledge"])

# First Run Experience / Setup Wizard
from .routes import first_run as first_run_routes
app.include_router(first_run_routes.router)

from .routes.analysis import analyse_htmx_handler  # noqa: E402


# ---------------------------------------------------------------------------
# First Run Experience: redirect first-time users to the Setup Wizard.
# Skips API, static, health, and the wizard itself. Settings can re-open
# the wizard at /setup?force=1 without being blocked.
# ---------------------------------------------------------------------------
@app.middleware("http")
async def first_run_middleware(request: Request, call_next):
    path = request.url.path or "/"
    if request.method == "GET" and not (
        path.startswith("/api")
        or path.startswith("/static")
        or path.startswith("/outputs")
        or path in ("/setup", "/health", "/favicon.ico")
        or path.startswith("/docs")
    ):
        # Allow force re-entry only via /setup; other pages redirect when needed
        try:
            from services.first_run_service import needs_first_run

            if needs_first_run():
                return RedirectResponse(url="/setup", status_code=307)
        except Exception:
            # Never block the app if FRE detection fails
            logger.debug("first_run_middleware: detection failed", exc_info=True)
    return await call_next(request)


@app.get("/setup", response_class=HTMLResponse)
async def setup_wizard_page(request: Request):
    """First Run Experience wizard (also Settings → Setup Wizard)."""
    return templates.TemplateResponse(request, "setup_wizard.html", {"request": request})


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    from services.history_service import HistoryService
    items = HistoryService().list_analyses(db, limit=6)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        _page_ctx(request, recent_items=items, stats={"recent": len(items), "batch": 0, "exports": 0}),
    )


@app.get("/analysis", response_class=HTMLResponse)
async def analysis_page(request: Request):
    return templates.TemplateResponse(request, "analysis.html", _page_ctx(request))


@app.get("/batch", response_class=HTMLResponse)
async def batch_page(request: Request):
    return templates.TemplateResponse(request, "batch.html", _page_ctx(request))


@app.get("/spectra", response_class=HTMLResponse)
async def spectra_page(request: Request):
    return templates.TemplateResponse(request, "spectra.html", _page_ctx(request))


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request, db: Session = Depends(get_db)):
    from services.history_service import HistoryService
    items = HistoryService().list_analyses(db, limit=100)
    return templates.TemplateResponse(request, "history.html", _page_ctx(request, items=items))


@app.get("/exports", response_class=HTMLResponse)
async def exports_page(request: Request):
    return templates.TemplateResponse(request, "exports.html", _page_ctx(request, export_profiles=EXPORT_PROFILES))


@app.get("/validation", response_class=HTMLResponse)
async def validation_page(request: Request):
    return templates.TemplateResponse(request, "validation.html", _page_ctx(request))


@app.get("/benchmarks", response_class=HTMLResponse)
async def benchmarks_page(request: Request):
    return templates.TemplateResponse(request, "benchmarks.html", _page_ctx(request))

@app.get("/virtual-screening", response_class=HTMLResponse)
async def virtual_screening_page(request: Request):
    return templates.TemplateResponse(request, "virtual_screening.html", _page_ctx(request))

# MedChem Workbench is a project-agnostic *series library*: a series enters a
# project by being linked to one of its campaigns, so this page stays unscoped.
@app.get("/medchem", response_class=HTMLResponse)
async def medchem_page(request: Request):
    return templates.TemplateResponse(request, "medchem_workbench.html", _page_ctx(request))


# ==========================================
# Project-scoped pages (Research Workflow Integration)
#
# Every route below takes its project from the URL via get_current_project,
# so a page cannot be rendered without its research context.
# ==========================================

@app.get("/projects", response_class=HTMLResponse)
async def projects_page(request: Request, db: Session = Depends(get_db)):
    from database.models import ResearchProject
    projects = db.query(ResearchProject).order_by(ResearchProject.created_at.desc()).all()
    return templates.TemplateResponse(request, "projects.html", _page_ctx(request, projects=projects))


@app.get("/project/{project_id}/research-os", response_class=HTMLResponse)
async def project_research_os(request: Request, project=Depends(get_current_project)):
    return templates.TemplateResponse(
        request, "research_os.html", _page_ctx(request, project=project, projects=[project])
    )


@app.get("/project/{project_id}/lead-opt", response_class=HTMLResponse)
async def project_lead_opt(request: Request, project=Depends(get_current_project), db: Session = Depends(get_db)):
    from services.campaign_service import CampaignService
    campaigns = CampaignService(db).campaigns_for_project(project.id)
    return templates.TemplateResponse(
        request, "lead_opt_studio.html", _page_ctx(request, project=project, campaigns=campaigns)
    )


@app.get("/project/{project_id}/admet", response_class=HTMLResponse)
async def project_admet(request: Request, project=Depends(get_current_project), db: Session = Depends(get_db)):
    from services.campaign_service import CampaignService
    series = CampaignService(db).series_for_project(project.id)
    return templates.TemplateResponse(
        request, "admet_workbench.html", _page_ctx(request, project=project, series=series)
    )


@app.get("/project/{project_id}/publication", response_class=HTMLResponse)
async def project_publication(request: Request, project=Depends(get_current_project), db: Session = Depends(get_db)):
    from services.campaign_service import CampaignService
    from services.publication_service import DOCX_AVAILABLE
    campaigns = CampaignService(db).campaigns_for_project(project.id)
    return templates.TemplateResponse(
        request,
        "publication_studio.html",
        _page_ctx(request, project=project, projects=[project], campaigns=campaigns, docx_available=DOCX_AVAILABLE),
    )


@app.get("/project/{project_id}/knowledge-engine", response_class=HTMLResponse)
async def project_knowledge_engine(request: Request, project=Depends(get_current_project), db: Session = Depends(get_db)):
    from database.models import KnowledgeRule, RuleContradiction
    # Knowledge mining is cross-project by design; the project only scopes the view.
    rules = db.query(KnowledgeRule).order_by(KnowledgeRule.created_at.desc()).all()
    contradictions = db.query(RuleContradiction).filter_by(status="Unresolved").all()
    return templates.TemplateResponse(
        request,
        "knowledge_engine.html",
        _page_ctx(request, project=project, rules=rules, contradictions=contradictions),
    )


# Legacy unscoped URLs -> send the user to pick a project first.
@app.get("/research-os", response_class=RedirectResponse)
@app.get("/lead-opt", response_class=RedirectResponse)
@app.get("/admet", response_class=RedirectResponse)
@app.get("/publication", response_class=RedirectResponse)
@app.get("/knowledge-engine", response_class=RedirectResponse)
async def legacy_module_redirect():
    return RedirectResponse(url="/projects", status_code=307)


@app.get("/docking", response_class=HTMLResponse)
async def docking_page(request: Request):
    return templates.TemplateResponse(request, "docking.html", _page_ctx(request))


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse(request, "settings.html", _page_ctx(request))


@app.get("/docs", response_class=HTMLResponse)
async def docs_page(request: Request):
    return templates.TemplateResponse(request, "docs.html", _page_ctx(request))


@app.get("/visualization", response_class=HTMLResponse)
async def visualization_page(request: Request):
    return templates.TemplateResponse(request, "visualization.html", _page_ctx(request))


@app.get("/docking-workspace", response_class=HTMLResponse)
async def docking_workspace_page(request: Request):
    return templates.TemplateResponse(request, "docking_workspace.html", _page_ctx(request))


@app.get("/pose-analysis", response_class=HTMLResponse)
async def pose_analysis_page(request: Request):
    return templates.TemplateResponse(request, "pose_analysis.html", _page_ctx(request))


@app.post("/analyse", response_class=HTMLResponse)
async def analyse_page(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    return await analyse_htmx_handler(
        request,
        db=db,
        input_text=form.get("input_text", ""),
        input_method=form.get("input_method", "smiles"),
        name=form.get("name"),
        include_spectra=form.get("include_spectra", "true") in ("true", "on", "1", True),
        save_image=form.get("save_image", "") in ("true", "on", "1"),
        atom_numbering=form.get("atom_numbering", "") in ("true", "on", "1"),
        highlight_aromatic=form.get("highlight_aromatic", "") in ("true", "on", "1"),
    )


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "chemistry-companion",
        "version": "3.0.0",
        "visualization": {
            "available": VisualizationService.is_available(),
            "message": VisualizationService.unavailable_message() if not VisualizationService.is_available() else "ok"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.app:app", host="0.0.0.0", port=8000, reload=True)
