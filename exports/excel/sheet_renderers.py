"""Worksheet renderers for normalized scientific export payloads."""

from __future__ import annotations

from typing import Any

from openpyxl import Workbook

from exports.excel.formatters import display_header, safe_cell_value
from exports.excel.styles import (
    apply_table_features,
    autosize_columns,
    style_data_rows,
    style_header_row,
)
from exports.schemas.batch_export_schema import BatchExportPayload
from exports.schemas.workbook_models import (
    CARBON_NMR,
    DESCRIPTORS,
    FAILED_ENTRIES,
    FUNCTIONAL_GROUPS,
    IR_PREDICTIONS,
    METADATA,
    MOLECULES,
    PROTON_NMR,
    SUMMARY,
)


SUMMARY_KEYS = [
    "record_id",
    "name",
    "smiles",
    "formula",
    "molecular_weight",
    "logp",
    "tpsa",
    "hbd",
    "hba",
    "ro5_pass",
    "functional_group_count",
    "ir_band_count",
    "proton_nmr_signal_count",
    "carbon_nmr_signal_count",
    "status",
    "error",
]

MOLECULE_KEYS = [
    "record_id",
    "row_index",
    "name",
    "smiles",
    "inchi",
    "inchikey",
    "formula",
    "molecular_weight",
    "exact_mass",
    "num_atoms",
    "num_heavy_atoms",
    "num_rings",
    "is_aromatic",
]

DESCRIPTOR_KEYS = [
    "record_id",
    "name",
    "smiles",
    "formula",
    "molecular_weight",
    "exact_mass",
    "logp",
    "tpsa",
    "hbd",
    "hba",
    "rotatable_bonds",
    "ring_count",
    "heavy_atom_count",
    "formal_charge",
    "fraction_csp3",
    "bertz_ct",
    "ro5_pass",
    "ro5_violations",
    "heterocycles_detected",
]

FUNCTIONAL_GROUP_KEYS = [
    "record_id",
    "name",
    "smiles",
    "group_name",
    "group_key",
    "category",
    "count",
    "atom_indices",
]

IR_KEYS = [
    "record_id",
    "name",
    "smiles",
    "assignment",
    "lower_cm1",
    "upper_cm1",
    "intensity",
    "confidence",
    "note",
]

PROTON_KEYS = [
    "record_id",
    "name",
    "smiles",
    "environment",
    "shift_ppm",
    "multiplicity",
    "integration",
    "atom_indices",
    "notes",
]

CARBON_KEYS = [
    "record_id",
    "name",
    "smiles",
    "environment",
    "shift_ppm",
    "shift_low_ppm",
    "shift_high_ppm",
    "carbon_count",
    "attached_elements",
    "attached_hydrogens",
    "is_quaternary",
    "notes",
]

FAILURE_KEYS = ["record_id", "row_index", "input", "name", "smiles", "error", "stage"]
METADATA_KEYS = ["key", "value"]


def render_sheet(wb: Workbook, title: str, payload: BatchExportPayload) -> None:
    rows, keys = _rows_for_sheet(title, payload)
    ws = wb.create_sheet(title)
    headers = [display_header(key) for key in keys]
    ws.append(headers)
    for row in rows:
        ws.append([safe_cell_value(row.get(key)) for key in keys])

    style_header_row(ws, headers)
    style_data_rows(ws, keys)
    apply_table_features(ws)
    autosize_columns(ws)


def _rows_for_sheet(title: str, payload: BatchExportPayload) -> tuple[list[dict[str, Any]], list[str]]:
    if title == SUMMARY:
        return payload.summary_rows(), SUMMARY_KEYS
    if title == MOLECULES:
        return payload.molecules, MOLECULE_KEYS
    if title == DESCRIPTORS:
        return payload.descriptors, DESCRIPTOR_KEYS
    if title == FUNCTIONAL_GROUPS:
        return payload.functional_groups, FUNCTIONAL_GROUP_KEYS
    if title == IR_PREDICTIONS:
        return payload.ir_predictions, IR_KEYS
    if title == PROTON_NMR:
        return payload.proton_nmr_predictions, PROTON_KEYS
    if title == CARBON_NMR:
        return payload.carbon_nmr_predictions, CARBON_KEYS
    if title == FAILED_ENTRIES:
        return payload.failures, FAILURE_KEYS
    if title == METADATA:
        return _metadata_rows(payload), METADATA_KEYS
    raise ValueError(f"Unknown workbook sheet: {title}")


def _metadata_rows(payload: BatchExportPayload) -> list[dict[str, Any]]:
    return [{"key": key, "value": value} for key, value in payload.metadata.items()]
