"""
api/routes/export.py
====================
Dedicated scientific export endpoints.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.models import get_db
from services.history_service import HistoryService
from exports.exporters import CsvExporter, ExcelExporter, JsonExporter
from exports.schemas.batch_export_schema import BatchExportPayload
from exports.schemas.workbook_models import list_profiles, resolve_profile
from services import ExportService

logger = logging.getLogger(__name__)
router = APIRouter()
export_service = ExportService()
csv_exporter = CsvExporter()
json_exporter = JsonExporter()
excel_exporter = ExcelExporter()
EXPORT_HISTORY: list[dict[str, Any]] = []


class ExportRequest(BaseModel):
    data: Dict[str, Any] | List[Dict[str, Any]]
    format: str = "xlsx"
    profile: str = "full"
    include_spectra: bool = True


def _timestamped_name(fmt: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    ext = {"excel": "xlsx", "markdown": "md"}.get(fmt.lower(), fmt.lower())
    return f"chemistry_companion_{ts}.{ext}"


def _media_type(fmt: str) -> str:
    if fmt == "json":
        return "application/json"
    if fmt == "csv":
        return "text/csv"
    if fmt in {"xlsx", "excel"}:
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if fmt == "markdown":
        return "text/markdown"
    raise HTTPException(status_code=400, detail=f"Unsupported format: {fmt}")


def _record_history(filename: str, fmt: str, profile: str, payload: BatchExportPayload) -> None:
    EXPORT_HISTORY.append({
        "filename": filename,
        "format": fmt,
        "profile": resolve_profile(profile).name,
        "records": payload.metadata.get("total_records", 0),
        "successful": payload.metadata.get("successful_records", 0),
        "failed": payload.metadata.get("failed_records", 0),
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "complete",
    })
    del EXPORT_HISTORY[:-50]


def _markdown_from_payload(payload: BatchExportPayload) -> str:
    lines = [
        "# Chemistry Companion Export",
        "",
        "## Summary",
        "",
    ]
    for key in ("total_records", "successful_records", "failed_records", "generated_at_utc"):
        lines.append(f"- **{key.replace('_', ' ').title()}:** {payload.metadata.get(key, '')}")
    lines.extend(["", "## Molecules", ""])
    for row in payload.summary_rows():
        status = row.get("status", "")
        lines.append(
            f"- **{row.get('name') or 'Molecule'}** `{row.get('smiles', '')}` "
            f"{row.get('formula') or ''} ({status})"
        )
        if row.get("error"):
            lines.append(f"  - Error: {row['error']}")
    lines.extend(["", "> Spectral predictions are heuristic and approximate."])
    return "\n".join(lines)


async def _render_export(request: ExportRequest) -> tuple[bytes, BatchExportPayload, str]:
    fmt = request.format.lower()
    payload = export_service.build_payload(
        request.data,
        metadata={
            "requested_format": fmt,
            "requested_profile": resolve_profile(request.profile).name,
            "include_spectra": request.include_spectra,
        },
    )

    if fmt == "json":
        return json_exporter.to_bytes(payload), payload, fmt
    if fmt == "csv":
        return csv_exporter.to_bytes(payload), payload, fmt
    if fmt in {"xlsx", "excel"}:
        content = await asyncio.to_thread(excel_exporter.to_bytes, payload, request.profile)
        return content, payload, "xlsx"
    if fmt == "markdown":
        return _markdown_from_payload(payload).encode("utf-8"), payload, fmt
    raise HTTPException(status_code=400, detail=f"Unsupported format: {fmt}")


def _stream_bytes(content: bytes):
    yield content


async def _download_response(request: ExportRequest) -> StreamingResponse:
    if not request.data:
        raise HTTPException(status_code=400, detail="No data to export")

    content, payload, normalized_format = await _render_export(request)
    filename = _timestamped_name(normalized_format)
    _record_history(filename, normalized_format, request.profile, payload)

    return StreamingResponse(
        _stream_bytes(content),
        media_type=_media_type(normalized_format),
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content)),
            "X-Export-Format": normalized_format,
            "X-Export-Profile": resolve_profile(request.profile).key,
            "X-Export-Records": str(payload.metadata.get("total_records", 0)),
            "X-Export-Failures": str(payload.metadata.get("failed_records", 0)),
        },
    )


@router.post("/export")
async def export_results(request: ExportRequest):
    """Compatibility streaming endpoint for current GUI callers."""
    try:
        return await _download_response(request)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Export error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {exc}") from exc


@router.post("/export/download")
async def download_export(request: ExportRequest):
    """Dedicated streaming export endpoint."""
    return await export_results(request)


@router.post("/export/profile")
async def export_latest_history_profile(
    profile: str = Form("full"),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Export the most recent saved analysis using a selected profile."""
    history_items = HistoryService().list_analyses(db, limit=1)
    if not history_items:
        raise HTTPException(status_code=400, detail="No saved analyses available for export")

    payload = history_items[0]
    request = ExportRequest(data=payload, format="xlsx", profile=profile)
    return await _download_response(request)


@router.post("/export/preview")
async def preview_export(request: ExportRequest) -> Dict[str, Any]:
    """Return workbook preview data without generating a download."""
    if not request.data:
        raise HTTPException(status_code=400, detail="No data to preview")

    payload = export_service.build_payload(
        request.data,
        metadata={"requested_profile": resolve_profile(request.profile).name},
    )
    profile = resolve_profile(request.profile)
    rows = payload.summary_rows()
    return {
        "profile": profile.to_dict(),
        "summary": {
            "total_records": payload.metadata.get("total_records", 0),
            "successful_records": payload.metadata.get("successful_records", 0),
            "failed_records": payload.metadata.get("failed_records", 0),
            "functional_group_rows": payload.metadata.get("functional_group_rows", 0),
            "ir_prediction_rows": payload.metadata.get("ir_prediction_rows", 0),
            "proton_nmr_rows": payload.metadata.get("proton_nmr_rows", 0),
            "carbon_nmr_rows": payload.metadata.get("carbon_nmr_rows", 0),
        },
        "sheets": list(profile.sheets),
        "preview_rows": rows[:5],
    }


@router.get("/export/profiles")
async def export_profiles() -> Dict[str, Any]:
    return {"profiles": list_profiles()}


@router.get("/export/history")
async def export_history() -> Dict[str, Any]:
    return {"count": len(EXPORT_HISTORY), "items": list(reversed(EXPORT_HISTORY[-20:]))}


@router.get("/export/formats")
async def get_supported_formats() -> Dict[str, Any]:
    return {
        "formats": ["csv", "json", "xlsx", "markdown"],
        "profiles": list_profiles(),
        "descriptions": {
            "csv": "Summary table for spreadsheets and ELNs",
            "json": "Normalized BatchExportPayload for programmatic use",
            "xlsx": "Styled scientific workbook",
            "markdown": "Human-readable report",
        },
    }
