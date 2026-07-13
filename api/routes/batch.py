"""
api/routes/batch.py
===================
Batch molecule processing (file upload).

Accepts CSV / Excel / TXT uploads whose molecules are given as SMILES **or**
IUPAC / chemical names. Name inputs are resolved to SMILES automatically by the
analysis pipeline (offline OPSIN first, online fallbacks after), then the batch
is analysed and an enriched results file is written for download.
"""

from __future__ import annotations

import csv
import io
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.batch_processor import _detect_columns, _normalise_header
from services import BatchService

logger = logging.getLogger(__name__)

router = APIRouter()
batch_service = BatchService()

# Directory the service writes exports to (mirrors BatchService default).
BATCH_OUTPUT_DIR = Path("output/batch")

# Column headers (normalised) that identify a row label rather than a structure.
_LABEL_COLUMNS = {
    "s/n", "s.n", "s.n.", "sn", "serial", "serial_no", "sr", "sr.no", "sr_no",
    "sr no", "no", "no.", "#", "index", "entry", "label", "code", "compound_id",
}

# Heuristic: a token that looks like a SMILES string rather than a name.
_SMILES_HINT = re.compile(r"[=#\[\]()@+\\/]|^[A-Za-z0-9@+\-\[\]()=#$%.\\/]+$")


class BatchResultRow(BaseModel):
    """Single batch result (flat, UI-friendly)."""
    smiles: str = ""
    name: str = ""
    input_iupac: str = ""
    status: str = "failed"
    source: str = ""
    mw: float = 0.0
    formula: str = ""
    error: str = ""


class BatchResponse(BaseModel):
    """Batch processing response."""
    total: int
    successful: int
    partial: int = 0
    failed: int
    avg_mw: float = 0.0
    results: List[BatchResultRow] = []
    export_paths: Dict[str, str] = {}
    download_csv: Optional[str] = None
    download_xlsx: Optional[str] = None
    status: str = "complete"


# ── Upload parsing ────────────────────────────────────────────────────────────

def _pick_label_column(columns: List[str], smiles_col: Optional[str], name_col: Optional[str]) -> Optional[str]:
    """Find a human label column (e.g. 'S/N') distinct from structure columns."""
    for col in columns:
        if col in (smiles_col, name_col):
            continue
        if _normalise_header(str(col)) in _LABEL_COLUMNS:
            return col
    return None


def _looks_like_smiles(value: str) -> bool:
    """Cheap heuristic to classify a bare TXT token as SMILES vs a name."""
    token = value.strip()
    if not token or " " in token:
        return False
    return bool(_SMILES_HINT.search(token))


def _rows_to_molecules(rows: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Normalise tabular rows into pipeline inputs.

    Detects the SMILES and IUPAC/name columns case-insensitively (reusing the
    batch_processor detection), and emits ``{"smiles": ...}`` or
    ``{"iupac": ..., "name": <label>}`` dicts. SMILES always wins when present.
    """
    if not rows:
        return []

    columns = list(rows[0].keys())
    smiles_col, name_col = _detect_columns([str(c) for c in columns])
    # _detect_columns lowercases; map back to the original header objects.
    header_lookup = {_normalise_header(str(c)): c for c in columns}
    smiles_col = header_lookup.get(_normalise_header(smiles_col)) if smiles_col else None
    name_col = header_lookup.get(_normalise_header(name_col)) if name_col else None
    label_col = _pick_label_column(columns, smiles_col, name_col)

    if not smiles_col and not name_col:
        raise HTTPException(
            status_code=400,
            detail="No 'smiles' or 'iupac'/'name' column found. "
                   f"Columns seen: {', '.join(str(c) for c in columns)}",
        )

    molecules: List[Dict[str, str]] = []
    for i, row in enumerate(rows):
        smiles = str(row.get(smiles_col) or "").strip() if smiles_col else ""
        name_val = str(row.get(name_col) or "").strip() if name_col else ""
        label = str(row.get(label_col) or "").strip() if label_col else ""

        if smiles and smiles.lower() != "nan":
            molecules.append({"smiles": smiles, "name": label or name_val or f"Mol_{i+1}"})
        elif name_val and name_val.lower() != "nan":
            # Treat the detected name/IUPAC column as an IUPAC input so the
            # pipeline resolves it to a structure; label (if any) is the display name.
            molecules.append({"iupac": name_val, "name": label or name_val})
        # rows with neither a SMILES nor a name are skipped
    return molecules


def _parse_upload(file: UploadFile, content: bytes) -> List[Dict[str, str]]:
    """Parse an uploaded CSV / Excel / TXT file into normalised molecule inputs."""
    name = (file.filename or "").lower()

    if name.endswith(".csv"):
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
        return _rows_to_molecules(list(reader))

    if name.endswith((".xlsx", ".xls")):
        try:
            import pandas as pd
        except ImportError:
            raise HTTPException(status_code=500, detail="Excel support requires pandas + openpyxl.")
        try:
            df = pd.read_excel(io.BytesIO(content))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"Could not read Excel file: {exc}")
        df = df.where(pd.notnull(df), None)
        return _rows_to_molecules(df.to_dict("records"))

    # TXT (or anything else): one entry per line, classified as SMILES or name.
    molecules: List[Dict[str, str]] = []
    for i, raw in enumerate(content.decode("utf-8-sig").splitlines()):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if _looks_like_smiles(line):
            molecules.append({"smiles": line, "name": f"Mol_{i+1}"})
        else:
            molecules.append({"iupac": line, "name": line})
    return molecules


# ── Response formatting ───────────────────────────────────────────────────────

def _format_batch_response(result: Dict[str, Any]) -> BatchResponse:
    """Convert the service result dict into the flat API response.

    Distinguishes fully successful analyses from *partial* ones (structure
    resolved but a subsystem — descriptors / functional groups / spectra — is
    missing), and surfaces the resolved SMILES + resolution source for name inputs.
    """
    rows: List[BatchResultRow] = []
    mw_values: List[float] = []

    for item in result.get("results", []):
        inp = item.get("input", {}) or {}
        molecule = item.get("molecule", {}) or {}
        metadata = item.get("metadata", {}) or {}
        resolution = metadata.get("resolution", {}) or {}
        source = resolution.get("source", "") or ""
        input_iupac = inp.get("iupac", "") or ""
        # Prefer the resolved canonical SMILES (present for IUPAC inputs).
        smiles = molecule.get("smiles") or inp.get("smiles", "") or ""
        name = molecule.get("name") or inp.get("name", "") or ""

        if not item.get("success"):
            rows.append(BatchResultRow(
                smiles=smiles,
                name=name,
                input_iupac=input_iupac,
                source=source,
                status="failed",
                error=item.get("error", "Unknown error"),
            ))
            continue

        desc = item.get("descriptors")
        mw = 0.0
        formula = molecule.get("formula") or ""
        if desc is not None:
            if hasattr(desc, "molecular_weight"):
                mw = float(desc.molecular_weight or 0)
                formula = formula or str(desc.formula or "")
            elif isinstance(desc, dict):
                mw = float(desc.get("molecular_weight") or desc.get("mol_weight") or 0)
                formula = formula or str(desc.get("formula") or "")
        if mw:
            mw_values.append(mw)
            mw = round(mw, 2)

        warnings = list(metadata.get("warnings", []))
        errors = list(metadata.get("errors", []))

        is_partial = False
        missing_systems: List[str] = []
        if not item.get("descriptors"):
            is_partial = True
            missing_systems.append("descriptors")
        if not item.get("functional_groups"):
            is_partial = True
            missing_systems.append("functional_groups")
        if metadata.get("include_spectra", True):
            if not item.get("ir_prediction"):
                is_partial = True
                missing_systems.append("ir_prediction")
            if not item.get("proton_nmr_prediction"):
                is_partial = True
                missing_systems.append("proton_nmr_prediction")
            if not item.get("carbon_nmr_prediction"):
                is_partial = True
                missing_systems.append("carbon_nmr_prediction")

        all_issues = warnings + errors
        if missing_systems:
            all_issues.append("Missing subsystems: " + ", ".join(missing_systems))

        rows.append(BatchResultRow(
            smiles=smiles,
            name=name,
            input_iupac=input_iupac,
            source=source,
            status="partial" if is_partial else "success",
            mw=mw,
            formula=formula,
            error="; ".join(all_issues),
        ))

    total = result.get("total_molecules", len(rows))
    successful = sum(1 for r in rows if r.status == "success")
    partial = sum(1 for r in rows if r.status == "partial")
    failed = total - (successful + partial)
    avg_mw = sum(mw_values) / len(mw_values) if mw_values else 0.0

    export_paths = result.get("export_paths", {}) or {}
    return BatchResponse(
        total=total,
        successful=successful,
        partial=partial,
        failed=failed,
        avg_mw=round(avg_mw, 2),
        results=rows,
        export_paths=export_paths,
        download_csv=Path(export_paths["csv"]).name if export_paths.get("csv") else None,
        download_xlsx=Path(export_paths["xlsx"]).name if export_paths.get("xlsx") else None,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

async def _run_batch_upload(file: UploadFile, include_spectra: bool) -> BatchResponse:
    """Shared handler: parse an uploaded file, run the batch, format the response."""
    try:
        content = await file.read()
        molecules = _parse_upload(file, content)

        if not molecules:
            raise HTTPException(status_code=400, detail="No molecules found in file")
        if len(molecules) > 100:
            raise HTTPException(status_code=400, detail="Too many molecules (max 100)")

        result = batch_service.process_batch(
            molecules=molecules,
            include_spectra=include_spectra,
            export_formats=["csv", "xlsx"],
            output_dir=str(BATCH_OUTPUT_DIR),
        )
        return _format_batch_response(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")


@router.post("/batch", response_model=BatchResponse)
async def process_batch(
    file: UploadFile = File(...),
    include_spectra: bool = Form(False),
) -> BatchResponse:
    """Process a batch of molecules from an uploaded CSV / Excel / TXT file."""
    return await _run_batch_upload(file, include_spectra)


@router.post("/batch/upload", response_model=BatchResponse)
async def process_batch_upload(
    file: UploadFile = File(...),
    include_spectra: bool = Form(False),
) -> BatchResponse:
    """Alias of ``/batch`` (kept for API compatibility)."""
    return await _run_batch_upload(file, include_spectra)


@router.post("/batch/process", response_model=BatchResponse)
async def process_batch_process(
    file: UploadFile = File(...),
    include_spectra: bool = Form(False),
) -> BatchResponse:
    """Alias of ``/batch`` (kept for GUI compatibility)."""
    return await _run_batch_upload(file, include_spectra)


@router.get("/batch/download/{filename}")
async def download_batch_result(filename: str) -> FileResponse:
    """Serve a generated batch results file from the batch output directory."""
    safe_name = Path(filename).name  # guard against path traversal
    if safe_name != filename or not safe_name:
        raise HTTPException(status_code=400, detail="Invalid filename")

    output_root = BATCH_OUTPUT_DIR.resolve()
    target = (output_root / safe_name).resolve()
    if output_root not in target.parents or not target.is_file():
        raise HTTPException(status_code=404, detail="Result file not found")

    return FileResponse(str(target), filename=safe_name)
