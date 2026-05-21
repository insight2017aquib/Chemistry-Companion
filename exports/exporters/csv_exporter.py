"""CSV serialization for normalized export payloads."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

from exports.schemas.batch_export_schema import BatchExportPayload, build_batch_export_payload


class CsvExporter:
    """Serialize the normalized payload as a readable summary table."""

    def normalize(self, data: BatchExportPayload | Any) -> BatchExportPayload:
        return data if isinstance(data, BatchExportPayload) else build_batch_export_payload(data)

    def to_string(self, data: BatchExportPayload | Any) -> str:
        payload = self.normalize(data)
        rows = payload.summary_rows()
        if not rows:
            return ""

        fieldnames = list(rows[0].keys())
        for row in rows[1:]:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)

        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return buffer.getvalue()

    def to_bytes(self, data: BatchExportPayload | Any) -> bytes:
        return self.to_string(data).encode("utf-8")

    def export(self, data: BatchExportPayload | Any, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_string(data), encoding="utf-8")
        return target
