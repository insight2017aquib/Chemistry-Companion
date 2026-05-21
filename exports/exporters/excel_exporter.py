"""Excel serialization for normalized export payloads."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from exports.excel.workbook_builder import build_workbook_bytes
from exports.schemas.batch_export_schema import BatchExportPayload, build_batch_export_payload


class ExcelExporter:
    """Render a publication-quality scientific workbook with openpyxl."""

    def normalize(self, data: BatchExportPayload | Any) -> BatchExportPayload:
        return data if isinstance(data, BatchExportPayload) else build_batch_export_payload(data)

    def to_bytes(self, data: BatchExportPayload | Any, profile: str = "full") -> bytes:
        return build_workbook_bytes(self.normalize(data), profile=profile)

    def export(self, data: BatchExportPayload | Any, path: str | Path, profile: str = "full") -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.to_bytes(data, profile=profile))
        return target
