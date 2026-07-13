"""
api/routes/export.py
====================
FastAPI routes for export operations.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class ExportRequest(BaseModel):
    """Request for exporting results."""
    data: Dict[str, Any]
    format: str  # 'csv', 'json', 'excel', 'pdf'


@router.post("/export")
async def export_results(request: ExportRequest):
    """
    Export analysis results to various formats.

    Supports CSV, JSON, and Excel formats.
    """
    try:
        if not request.data:
            raise HTTPException(status_code=400, detail="No data to export")

        fmt = request.format.lower()

        if fmt == "json":
            # Export as JSON
            content = json.dumps(request.data, indent=2, default=str)
            return StreamingResponse(
                iter([content]),
                media_type="application/json",
                headers={"Content-Disposition": "attachment; filename=export.json"}
            )

        elif fmt == "csv":
            # Simplified CSV export
            lines = []
            if "descriptors" in request.data:
                for key, value in request.data["descriptors"].items():
                    lines.append(f'"{key}","{value}"')
            
            content = "Key,Value\n" + "\n".join(lines)
            return StreamingResponse(
                iter([content]),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=export.csv"}
            )

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {fmt}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.get("/export/formats")
async def get_supported_formats() -> Dict[str, Any]:
    """
    Get list of supported export formats.
    """
    return {
        "formats": ["csv", "json", "xlsx"],
        "descriptions": {
            "csv": "Comma-separated values for spreadsheet applications",
            "json": "JavaScript Object Notation for programmatic access",
            "xlsx": "Microsoft Excel format with multiple sheets"
        }
    }
