"""JSON serialization for normalized export payloads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from exports.schemas.batch_export_schema import BatchExportPayload, build_batch_export_payload


class JsonExporter:
    """Serialize the normalized BatchExportPayload for programmatic use."""

    def normalize(self, data: BatchExportPayload | Any) -> BatchExportPayload:
        return data if isinstance(data, BatchExportPayload) else build_batch_export_payload(data)

    def to_string(self, data: BatchExportPayload | Any) -> str:
        payload = self.normalize(data)
        return json.dumps(payload.to_dict(), indent=2, ensure_ascii=False, default=str)

    def to_bytes(self, data: BatchExportPayload | Any) -> bytes:
        return self.to_string(data).encode("utf-8")

    def export(self, data: BatchExportPayload | Any, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_string(data), encoding="utf-8")
        return target
