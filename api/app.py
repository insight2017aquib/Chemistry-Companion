"""
api/app.py — Chemistry Companion web application
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from api.templating import create_templates
from database.models import configure_database, get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
templates = create_templates(ROOT / "templates")

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
    db_path = ROOT / "chemistry_companion.db"
    configure_database(f"sqlite:///{db_path}")
    logger.info("Chemistry Companion started (db=%s)", db_path)
    yield


app = FastAPI(title="Chemistry Companion", version="2.0.0", lifespan=lifespan)

if (ROOT / "static").exists():
    app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")

if (ROOT / "outputs").exists():
    app.mount("/outputs", StaticFiles(directory=str(ROOT / "outputs")), name="outputs")

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
from .routes import docking_workspace as dock_ws_routes

# Visualization API: handles protein parsing, ligand 2D/3D generation, and overlay rendering
app.include_router(viz_routes.router, prefix="/api/visualization", tags=["visualization"])

# Docking Workspace API: handles protein prep, gridbox detection, Vina execution, and pose extraction
app.include_router(dock_ws_routes.router, prefix="/api/docking", tags=["docking-workspace"])

# LLM API: provides AI-powered pose explanation (degrades gracefully if API key is missing)
from .routes import llm_explanation as llm_routes
app.include_router(llm_routes.router, prefix="/api/llm", tags=["llm"])

from .routes.analysis import analyse_htmx_handler  # noqa: E402


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
    return {"status": "healthy", "service": "chemistry-companion", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.app:app", host="0.0.0.0", port=8000, reload=True)
