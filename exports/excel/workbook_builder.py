"""Build scientific Excel workbooks from normalized export payloads."""

from __future__ import annotations

import io
from copy import deepcopy
from typing import Any

from openpyxl import Workbook

from exports.excel.sheet_renderers import render_sheet
from exports.excel.styles import apply_workbook_properties
from exports.schemas.batch_export_schema import BatchExportPayload, build_batch_export_payload
from exports.schemas.workbook_models import resolve_profile


def _payload_from_any(data: BatchExportPayload | Any) -> BatchExportPayload:
    if isinstance(data, BatchExportPayload):
        cloned = BatchExportPayload(
            molecules=deepcopy(data.molecules),
            descriptors=deepcopy(data.descriptors),
            functional_groups=deepcopy(data.functional_groups),
            ir_predictions=deepcopy(data.ir_predictions),
            proton_nmr_predictions=deepcopy(data.proton_nmr_predictions),
            carbon_nmr_predictions=deepcopy(data.carbon_nmr_predictions),
            failures=deepcopy(data.failures),
            metadata=deepcopy(data.metadata),
        )
        return cloned
    return build_batch_export_payload(data)


def build_workbook(data: BatchExportPayload | Any, profile: str = "full") -> Workbook:
    """Create an openpyxl Workbook from normalized export data."""
    payload = _payload_from_any(data)
    export_profile = resolve_profile(profile)
    payload.metadata["profile"] = export_profile.name
    payload.metadata["profile_key"] = export_profile.key
    payload.metadata["workbook_sheets"] = ", ".join(export_profile.sheets)

    wb = Workbook()
    wb.remove(wb.active)
    apply_workbook_properties(wb, export_profile.name)

    for sheet_name in export_profile.sheets:
        render_sheet(wb, sheet_name, payload)

    if wb.worksheets:
        wb.active = 0
    return wb


def build_workbook_bytes(data: BatchExportPayload | Any, profile: str = "full") -> bytes:
    """Render a workbook into an in-memory XLSX byte stream."""
    workbook = build_workbook(data, profile=profile)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
