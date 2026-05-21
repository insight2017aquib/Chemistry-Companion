"""
api/routes/batch.py
===================
Batch molecule processing (file upload + JSON).
"""

from __future__ import annotations

import csv
import io
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel

from services import BatchService
from exports.schemas.batch_export_schema import build_batch_export_payload

logger = logging.getLogger(__name__)
router = APIRouter()
batch_service = BatchService()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))


class BatchRequest(BaseModel):
    molecules: List[Dict[str, str]]
    include_spectra: bool = True
    save_images: bool = False
    export_formats: List[str] = []


class BatchResultRow(BaseModel):
    smiles: str = ""
    name: str = ""
    status: str = "failed"
    mw: float = 0.0
    formula: str = ""
    error: str = ""


class BatchResponse(BaseModel):
    total: int
    successful: int
    failed: int
    avg_mw: float = 0.0
    results: List[BatchResultRow] = []
    export_paths: Dict[str, str] = {}
    status: str = "complete"


def _parse_upload(file: UploadFile, content: bytes) -> List[Dict[str, str]]:
    name = (file.filename or "").lower()
    if name.endswith(".csv"):
        reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
        rows = list(reader)
        molecules = []
        for row in rows:
            smiles = row.get("smiles") or row.get("SMILES") or row.get("Smiles")
            if smiles:
                molecules.append({
                    "smiles": smiles.strip(),
                    "name": row.get("name") or row.get("Name") or "",
                })
        return molecules

    if name.endswith((".xlsx", ".xls")):
        import pandas as pd
        df = pd.read_excel(io.BytesIO(content))
        molecules = []
        smiles_col = next((c for c in df.columns if str(c).lower() == "smiles"), None)
        if smiles_col is None:
            smiles_col = df.columns[0]
        name_col = next((c for c in df.columns if str(c).lower() == "name"), None)
        for _, row in df.iterrows():
            smi = str(row[smiles_col]).strip()
            if smi and smi.lower() != "nan":
                molecules.append({
                    "smiles": smi,
                    "name": str(row[name_col]) if name_col else "",
                })
        return molecules

    lines = content.decode("utf-8").strip().split("\n")
    return [
        {"smiles": line.strip(), "name": f"Mol_{i+1}"}
        for i, line in enumerate(lines)
        if line.strip()
    ]


def _format_batch_response(result: Dict[str, Any]) -> BatchResponse:
    rows: List[BatchResultRow] = []
    mw_values: List[float] = []

    for item in result.get("results", []):
        if item.get("success"):
            desc = item.get("descriptors")
            mw = 0.0
            formula = ""
            if desc is not None:
                if hasattr(desc, "molecular_weight"):
                    mw = float(desc.molecular_weight or 0)
                    formula = str(desc.formula or "")
                elif isinstance(desc, dict):
                    mw = float(desc.get("molecular_weight") or desc.get("mol_weight") or 0)
                    formula = str(desc.get("formula") or "")
            if mw:
                mw_values.append(mw)
            inp = item.get("input", {})
            rows.append(BatchResultRow(
                smiles=inp.get("smiles", ""),
                name=inp.get("name", ""),
                status="success",
                mw=mw,
                formula=formula,
            ))
        else:
            inp = item.get("input", {})
            rows.append(BatchResultRow(
                smiles=inp.get("smiles", ""),
                name=inp.get("name", ""),
                status="failed",
                error=item.get("error", "Unknown error"),
            ))

    total = result.get("total_molecules", len(rows))
    successful = result.get("successful_analyses", sum(1 for r in rows if r.status == "success"))
    failed = result.get("failed_analyses", total - successful)
    avg_mw = sum(mw_values) / len(mw_values) if mw_values else 0.0

    return BatchResponse(
        total=total,
        successful=successful,
        failed=failed,
        avg_mw=round(avg_mw, 2),
        results=rows,
        export_paths=result.get("export_paths", {}),
    )


@router.post("/batch", response_model=BatchResponse)
async def process_batch_json(request: BatchRequest) -> BatchResponse:
    """Process batch from JSON molecule list."""
    if not request.molecules:
        raise HTTPException(status_code=400, detail="No molecules provided")
    if len(request.molecules) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 molecules per batch")

    result = batch_service.process_batch(
        molecules=request.molecules,
        include_spectra=request.include_spectra,
        save_images=request.save_images,
        export_formats=request.export_formats,
    )
    return _format_batch_response(result)


@router.post("/batch/upload", response_model=BatchResponse)
async def process_batch_upload(
    file: UploadFile = File(...),
    include_spectra: bool = Form(False),
) -> BatchResponse:
    """Process batch from uploaded CSV, Excel, or TXT."""
    content = await file.read()
    molecules = _parse_upload(file, content)
    if not molecules:
        raise HTTPException(status_code=400, detail="No molecules found in file")
    if len(molecules) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 molecules per batch")

    result = batch_service.process_batch(
        molecules=molecules,
        include_spectra=include_spectra,
    )
    return _format_batch_response(result)


@router.post("/batch/process", response_class=HTMLResponse, include_in_schema=False)
async def process_batch_htmx(
    request: Request,
    file: UploadFile = File(...),
    include_spectra: bool = Form(False),
):
    """HTMX partial for batch results."""
    try:
        content = await file.read()
        molecules = _parse_upload(file, content)
        if not molecules:
            return templates.TemplateResponse(
                request,
                "components/error_banner.html",
                {"request": request, "message": "No molecules found in file"},
                status_code=400,
            )
        result = batch_service.process_batch(
            molecules=molecules[:100],
            include_spectra=include_spectra,
        )
        response = _format_batch_response(result)
        export_payload = build_batch_export_payload(
            result,
            metadata={"export_context": "batch_htmx"},
        )
        return templates.TemplateResponse(
            request,
            "components/batch_results.html",
            {
                "request": request,
                "batch": response.model_dump(),
                "export_json": json.dumps(export_payload.to_dict(), default=str),
            },
        )
    except Exception as e:
        logger.error("Batch HTMX failed: %s", e, exc_info=True)
        return templates.TemplateResponse(
            request,
            "components/error_banner.html",
            {"request": request, "message": str(e)},
            status_code=500,
        )
