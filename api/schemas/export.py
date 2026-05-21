"""
api/schemas/export.py
=====================
Pydantic schemas for export requests and responses.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExportRequest(BaseModel):
    """Request for exporting analysis results."""

    analysis_ids: List[str] = Field(
        ...,
        description="List of analysis IDs to export"
    )
    formats: List[str] = Field(
        default_factory=lambda: ["csv"],
        description="Export formats"
    )
    include_spectra: bool = Field(True, description="Include spectral data")
    output_dir: Optional[str] = Field(None, description="Output directory")

    class Config:
        schema_extra = {
            "example": {
                "analysis_ids": ["analysis_001", "analysis_002"],
                "formats": ["csv", "json", "xlsx"],
                "include_spectra": True
            }
        }


class ExportResponse(BaseModel):
    """Response for export operation."""

    success: bool
    export_paths: Dict[str, str] = Field(default_factory=dict)
    total_exports: int = 0
    errors: List[str] = Field(default_factory=list)

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "export_paths": {
                    "csv": "/exports/analysis_results.csv",
                    "json": "/exports/analysis_results.json"
                },
                "total_exports": 2
            }
        }


class ExportPreviewResponse(BaseModel):
    """Structured response for workbook preview endpoints."""

    profile: Dict[str, Any]
    summary: Dict[str, Any]
    sheets: List[str]
    preview_rows: List[Dict[str, Any]] = Field(default_factory=list)
