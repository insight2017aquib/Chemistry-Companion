"""
services/excel_report_service.py
================================
Compatibility wrapper for the normalized scientific workbook exporter.
"""

from __future__ import annotations

from typing import Any

from exports.exporters.excel_exporter import ExcelExporter


def export_workbook(records: list[dict[str, Any]], profile: str = "full") -> bytes:
    """Build a styled multi-sheet workbook in memory."""
    return ExcelExporter().to_bytes(records, profile=profile)
