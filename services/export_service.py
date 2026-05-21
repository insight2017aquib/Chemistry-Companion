"""
services/export_service.py
=========================
Service layer for normalized export operations.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from exports.exporters import CsvExporter, ExcelExporter, JsonExporter
from exports.schemas.batch_export_schema import BatchExportPayload, build_batch_export_payload

logger = logging.getLogger(__name__)


class ExportService:
    """Service for handling scientific exports from a shared payload."""

    def __init__(self):
        self.csv_exporter = CsvExporter()
        self.json_exporter = JsonExporter()
        self.excel_exporter = ExcelExporter()

    def build_payload(
        self,
        analysis_results: Any,
        *,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BatchExportPayload:
        return build_batch_export_payload(analysis_results, metadata=metadata or {})

    def export_results(
        self,
        analysis_results: List[Dict[str, Any]],
        formats: List[str],
        output_dir: Optional[str] = None,
        include_spectra: bool = True,
        profile: str = "full",
    ) -> Dict[str, str]:
        """
        Export analysis results to requested formats using the normalized payload.
        """
        output_path = Path(output_dir) if output_dir else Path("output/exports")
        output_path.mkdir(parents=True, exist_ok=True)

        payload = self.build_payload(
            analysis_results,
            metadata={"include_spectra": include_spectra, "profile": profile},
        )
        export_paths: Dict[str, str] = {}

        for fmt in formats:
            normalized = fmt.lower()
            try:
                if normalized == "csv":
                    path = self.csv_exporter.export(payload, output_path / "analysis_results.csv")
                    export_paths["csv"] = str(path)
                elif normalized == "json":
                    path = self.json_exporter.export(payload, output_path / "analysis_results.json")
                    export_paths["json"] = str(path)
                elif normalized in {"xlsx", "excel"}:
                    path = self.excel_exporter.export(payload, output_path / "analysis_results.xlsx", profile=profile)
                    export_paths["xlsx"] = str(path)
            except Exception as exc:
                logger.error("Failed to export %s: %s", fmt, exc, exc_info=True)

        return export_paths

    def _flatten_result(self, result: Dict[str, Any], include_spectra: bool) -> Dict[str, Any]:
        """
        Backward-compatible one-row summary used by legacy callers.

        The row is still produced from BatchExportPayload, so flattening rules stay
        centralized and do not leak nested dictionaries into CSV cells.
        """
        payload = self.build_payload([result], metadata={"include_spectra": include_spectra})
        rows = payload.summary_rows()
        return rows[0] if rows else {}
