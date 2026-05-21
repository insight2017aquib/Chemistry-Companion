"""
api/routes/analysis.py
======================
Molecule analysis API and HTMX handlers.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.serializers import serialize_analysis_result
from database.models import get_db
from services import AnalysisService
from services.history_service import HistoryService
from core.resolver import resolve_molecule_input

logger = logging.getLogger(__name__)

router = APIRouter()
analysis_service = AnalysisService()
history_service = HistoryService()

templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))


class MoleculeInput(BaseModel):
    smiles: Optional[str] = None
    inchi: Optional[str] = None
    iupac: Optional[str] = None
    name: Optional[str] = None


class AnalysisRequest(BaseModel):
    molecule: MoleculeInput
    include_spectra: bool = True
    save_image: bool = False
    save_history: bool = True
    export_formats: list[str] = []


def _parse_molecule_input(
    smiles: Optional[str] = None,
    inchi: Optional[str] = None,
    iupac: Optional[str] = None,
    name: Optional[str] = None,
    input_text: Optional[str] = None,
    input_method: Optional[str] = None,
) -> MoleculeInput:
    """Normalize form/JSON inputs into MoleculeInput."""
    if input_text and input_method:
        text = input_text.strip()
        if input_method == "smiles":
            smiles = text
        elif input_method == "inchi":
            inchi = text
        elif input_method in ("name", "iupac"):
            iupac = text
    return MoleculeInput(smiles=smiles, inchi=inchi, iupac=iupac, name=name)


def _run_analysis(
    mol: MoleculeInput,
    include_spectra: bool = True,
    save_image: bool = False,
) -> dict[str, Any]:
    result = analysis_service.analyze_molecule(
        smiles=mol.smiles,
        inchi=mol.inchi,
        iupac=mol.iupac,
        name=mol.name,
        include_spectra=include_spectra,
        save_image=save_image,
    )
    if result.metadata.get("error"):
        raise HTTPException(status_code=400, detail=result.metadata["error"])
    if result.molecule is None:
        raise HTTPException(status_code=400, detail="Could not parse molecule input")
    return serialize_analysis_result(result)


@router.post("/analyze")
@router.post("/analyse")
async def analyze_molecule_json(
    request: AnalysisRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """JSON analysis endpoint."""
    try:
        raw = analysis_service.analyze_molecule(
            smiles=request.molecule.smiles,
            inchi=request.molecule.inchi,
            iupac=request.molecule.iupac,
            name=request.molecule.name,
            include_spectra=request.include_spectra,
            save_image=request.save_image,
        )
        if raw.metadata.get("error"):
            raise HTTPException(
                status_code=400,
                detail={
                    "message": raw.metadata["error"],
                    "resolution": raw.metadata.get("resolution"),
                },
            )
        if raw.molecule is None:
            # Try a best-effort resolution for more helpful feedback
            input_text = (
                request.molecule.smiles or request.molecule.inchi or request.molecule.iupac or request.molecule.name or ""
            )
            resol = resolve_molecule_input(input_text) if input_text else None
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Could not parse molecule input",
                    "resolution": getattr(resol, "__dict__", None),
                },
            )
        if request.save_history:
            history_service.save_analysis(db, raw)
        return serialize_analysis_result(raw)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Analysis failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}") from e


@router.post("/resolve")
async def resolve_input(payload: dict) -> dict:
    """Resolve an arbitrary input string to canonical SMILES and source info."""
    text = payload.get("input_text") or payload.get("text") or ""
    if not text:
        return {"success": False, "error": "No input provided"}
    try:
        res = resolve_molecule_input(text)
        return {
            "success": bool(res.success),
            "input": res.input_text,
            "detected_type": res.detected_type,
            "canonical_smiles": res.canonical_smiles,
            "source": res.source,
            "error": res.error,
        }
    except Exception as exc:
        logger.debug("Resolve failed: %s", exc, exc_info=True)
        return {"success": False, "error": str(exc)}


async def analyse_htmx_handler(
    request: Request,
    db: Session,
    input_text: str = "",
    input_method: str = "smiles",
    name: Optional[str] = None,
    include_spectra: bool = True,
    save_image: bool = False,
    atom_numbering: bool = False,
    highlight_aromatic: bool = False,
):
    """HTMX partial: run analysis and return results panel."""
    mol = _parse_molecule_input(
        name=name,
        input_text=input_text,
        input_method=input_method,
    )
    try:
        raw = analysis_service.analyze_molecule(
            smiles=mol.smiles,
            inchi=mol.inchi,
            iupac=mol.iupac,
            name=mol.name,
            include_spectra=include_spectra,
            save_image=save_image,
        )
        if raw.metadata.get("error"):
            return templates.TemplateResponse(
                "components/error_banner.html",
                {
                    "request": request,
                    "message": raw.metadata["error"],
                    "resolution": raw.metadata.get("resolution"),
                },
                status_code=400,
            )
        if raw.molecule is None:
            return templates.TemplateResponse(
                "components/error_banner.html",
                {"request": request, "message": "Could not parse molecule input"},
                status_code=400,
            )
        history_service.save_analysis(db, raw)
        payload = serialize_analysis_result(raw)
        smiles = payload["molecule"].get("smiles", "")
        import json
        ir_bands = (payload.get("ir_prediction") or {}).get("bands", [])
        return templates.TemplateResponse(
            "components/analysis_results.html",
            {
                "request": request,
                "result": payload,
                "export_json": json.dumps(payload),
                "ir_bands_json": json.dumps(ir_bands),
                "smiles": smiles,
                "atom_numbering": atom_numbering,
                "highlight_aromatic": highlight_aromatic,
            },
        )
    except Exception as e:
        logger.error("HTMX analysis failed: %s", e, exc_info=True)
        return templates.TemplateResponse(
            "components/error_banner.html",
            {"request": request, "message": str(e)},
            status_code=500,
        )


@router.get("/examples")
async def get_example_molecules() -> Dict[str, Any]:
    """Example molecules for quick selection."""
    examples = analysis_service.get_example_molecules()
    return {
        "examples": [
            {"id": k, **v}
            for k, v in examples.items()
            if k in ("benzene", "caffeine", "aspirin", "quinoxaline")
        ]
    }


@router.post("/funcgroups")
async def functional_groups(request: AnalysisRequest) -> dict[str, Any]:
    """Functional group analysis only."""
    raw = analysis_service.analyze_molecule(
        smiles=request.molecule.smiles,
        inchi=request.molecule.inchi,
        iupac=request.molecule.iupac,
        name=request.molecule.name,
        include_spectra=False,
    )
    payload = serialize_analysis_result(raw)
    return {
        "functional_groups": payload.get("functional_groups", {}),
        "functional_group_report": payload.get("functional_group_report", {}),
        "status": "success",
    }
