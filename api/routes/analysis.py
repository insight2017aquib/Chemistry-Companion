"""
api/routes/analysis.py
======================
FastAPI routes for molecule analysis.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from api.templating import create_templates
from core.paths import templates_dir
from services import AnalysisService

logger = logging.getLogger(__name__)

router = APIRouter()
analysis_service = AnalysisService()
templates = create_templates(templates_dir())


class MoleculeInput(BaseModel):
    """Input for molecule analysis."""
    smiles: Optional[str] = None
    inchi: Optional[str] = None
    iupac: Optional[str] = None
    name: Optional[str] = None


class AnalysisRequest(BaseModel):
    """Request for complete molecule analysis."""
    molecule: MoleculeInput
    include_spectra: bool = True
    save_image: bool = False
    export_formats: list[str] = []


class AnalysisResponse(BaseModel):
    """Analysis response."""
    molecule: Dict[str, Any]
    descriptors: Dict[str, Any]
    functional_groups: Dict[str, Any]
    spectra: Dict[str, Any] = {}
    status: str = "success"


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_molecule(request: AnalysisRequest) -> AnalysisResponse:
    """
    Analyze a single molecule.

    Performs complete molecular analysis including descriptors,
    functional groups, and spectral predictions.
    """
    try:
        # Extract molecule input
        mol_input = request.molecule
        
        # Run analysis
        result = analysis_service.analyze_molecule(
            smiles=mol_input.smiles,
            inchi=mol_input.inchi,
            iupac=mol_input.iupac,
            name=mol_input.name,
            include_spectra=request.include_spectra,
            save_image=request.save_image,
            export_formats=request.export_formats,
        )

        # Format response
        descriptors = result.descriptors or {}
        fg_report = result.functional_group_report or {}
        
        return AnalysisResponse(
            molecule={
                "smiles": mol_input.smiles or "N/A",
                "inchi": mol_input.inchi or "N/A",
                "name": mol_input.name or "Unknown",
                "formula": descriptors.get("formula", "N/A"),
            },
            descriptors={
                "formula": descriptors.get("formula"),
                "molecular_weight": descriptors.get("mol_weight"),
                "exact_mass": descriptors.get("exact_mass"),
                "logp": descriptors.get("logp"),
                "tpsa": descriptors.get("tpsa"),
                "hbd": descriptors.get("hbd"),
                "hba": descriptors.get("hba"),
                "rotatable_bonds": descriptors.get("rotatable_bonds"),
                "ring_count": descriptors.get("ring_count"),
            },
            functional_groups={
                "keys": fg_report.get("keys", []),
                "names": fg_report.get("names", []),
                "counts": fg_report.get("counts", {}),
                "summary": fg_report.get("summary_text", ""),
            },
            spectra={
                "ir": result.ir_prediction,
                "proton_nmr": result.proton_nmr_prediction,
                "carbon_nmr": result.carbon_nmr_prediction,
            } if request.include_spectra else {},
            status="success"
        )

    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


async def analyse_htmx_handler(
    request: Request,
    db=None,
    input_text: str = "",
    input_method: str = "smiles",
    name: Optional[str] = None,
    include_spectra: bool = True,
    save_image: bool = False,
    atom_numbering: bool = False,
    highlight_aromatic: bool = False,
):
    """Render the analysis result partial used by the HTMX frontend."""
    text = (input_text or "").strip()
    if not text:
        return HTMLResponse(
            '<div class="p-4 text-sm text-red-700">Please provide a molecule input.</div>',
            status_code=400,
        )

    input_method = (input_method or "smiles").lower()
    kwargs = {
        "smiles": None,
        "inchi": None,
        "iupac": None,
        "name": name,
        "include_spectra": include_spectra,
        "save_image": save_image,
    }
    if input_method in {"inchi", "iupac", "name"}:
        kwargs[input_method] = text
    else:
        kwargs["smiles"] = text

    result = analysis_service.analyze_molecule(**kwargs)
    if not result.molecule:
        message = result.metadata.get("error", "Analysis failed.")
        return HTMLResponse(
            f'<div class="p-4 text-sm text-red-700">{message}</div>',
            status_code=200,
        )

    return templates.TemplateResponse(
        request,
        "components/analysis_results.html",
        {"result": result},
    )


@router.post("/analyse", response_class=HTMLResponse)
async def analyse_htmx_route(request: Request):
    """Compatibility endpoint for the existing HTMX single-analysis form."""
    form = await request.form()
    return await analyse_htmx_handler(
        request,
        input_text=form.get("input_text", ""),
        input_method=form.get("input_method") or form.get("input_type", "smiles"),
        name=form.get("name"),
        include_spectra=form.get("include_spectra", "true") in ("true", "on", "1", True),
        save_image=form.get("save_image", "") in ("true", "on", "1"),
        atom_numbering=form.get("atom_numbering", "") in ("true", "on", "1"),
        highlight_aromatic=form.get("highlight_aromatic", "") in ("true", "on", "1"),
    )




@router.get("/examples")
async def get_example_molecules() -> Dict[str, Any]:
    """
    Get example molecules for quick selection.
    """
    return {
        "examples": [
            {"name": "Benzene", "smiles": "c1ccccc1"},
            {"name": "Caffeine", "smiles": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"},
            {"name": "Aspirin", "smiles": "CC(=O)Oc1ccccc1C(=O)O"},
            {"name": "Quinoxaline", "smiles": "c1cc2cccnc2nc1"},
            {"name": "Ethanol", "smiles": "CCO"},
            {"name": "Acetone", "smiles": "CC(=O)C"},
        ]
    }
