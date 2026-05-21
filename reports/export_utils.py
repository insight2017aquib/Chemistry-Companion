"""
reports/export_utils.py
=======================

Export MoleculeRecord + DescriptorRecord pairs to CSV, JSON, and XLSX.
"""

from __future__ import annotations

import csv
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def mol_row(mol_rec, desc_rec) -> dict[str, Any]:
    """Return a flat, CSV-friendly dict for one molecule."""
    row: dict[str, Any] = {
        "name": getattr(mol_rec, "name", "") or "",
        "smiles": getattr(mol_rec, "smiles", "") or "",
        "inchi": getattr(mol_rec, "inchi", "") or "",
        "inchikey": getattr(mol_rec, "inchikey", "") or "",
        "formula": getattr(mol_rec, "formula", "") or "",
        "mol_weight": getattr(mol_rec, "mol_weight", None),
        "exact_mass": getattr(mol_rec, "exact_mass", None),
        "num_atoms": getattr(mol_rec, "num_atoms", None),
        "num_heavy_atoms": getattr(mol_rec, "num_heavy_atoms", None),
        "num_bonds": getattr(mol_rec, "num_bonds", None),
        "num_rings": getattr(mol_rec, "num_rings", None),
        "is_aromatic": getattr(mol_rec, "is_aromatic", None),
    }

    atom_counts = getattr(mol_rec, "atom_counts", None) or {}
    for sym, cnt in sorted(atom_counts.items()):
        row[f"atom_{sym}"] = cnt

    if desc_rec is not None:
        for attr in (
            "logp",
            "tpsa",
            "hbd",
            "hba",
            "rotatable_bonds",
            "bertz_ct",
            "lipinski_pass",
            "lipinski_violations",
        ):
            if hasattr(desc_rec, attr):
                row[attr] = getattr(desc_rec, attr)

        functional_groups = getattr(desc_rec, "functional_groups", None) or {}
        if isinstance(functional_groups, dict):
            row["functional_groups"] = "; ".join(
                f"{k}: {v}" for k, v in functional_groups.items()
            )
        else:
            row["functional_groups"] = str(functional_groups)

    return row


build_export_row = mol_row


def record_to_dict(mol_rec, desc_rec=None) -> dict[str, Any]:
    row: dict[str, Any] = {
        "Name": getattr(mol_rec, "name", "") or "",
        "SMILES": getattr(mol_rec, "smiles", "") or "",
        "Formula": getattr(desc_rec, "formula", None) or getattr(mol_rec, "formula", "") or "",
        "MW (Da)": getattr(desc_rec, "molecular_weight", None) or getattr(mol_rec, "mol_weight", None) or "",
        "LogP": getattr(desc_rec, "logp", ""),
        "TPSA (A2)": getattr(desc_rec, "tpsa", ""),
        "HBD": getattr(desc_rec, "hbd", ""),
        "HBA": getattr(desc_rec, "hba", ""),
        "Total Atoms": getattr(mol_rec, "num_atoms", ""),
        "Heavy Atoms": getattr(mol_rec, "num_heavy_atoms", ""),
        "Ro5 Pass": getattr(desc_rec, "ro5_pass", ""),
        "Ro5 Violations": getattr(desc_rec, "ro5_violations", ""),
    }

    if desc_rec is not None and hasattr(desc_rec, "ro5_details"):
        for rule, details in desc_rec.ro5_details.items():
            row[f"Ro5: {rule}"] = details.get("pass", "")

    functional_groups = getattr(desc_rec, "functional_groups", None)
    if isinstance(functional_groups, dict):
        row["Functional Groups"] = "; ".join(
            f"{k}: {v}" for k, v in sorted(functional_groups.items())
        )
    else:
        row["Functional Groups"] = str(functional_groups) if functional_groups is not None else ""

    return row


def build_dataframe(rows: list[dict[str, Any]]) -> "pd.DataFrame":
    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError("pandas is required for build_dataframe") from exc
    return pd.DataFrame(rows)


def export_csv(df, path: str) -> str:
    try:
        df.to_csv(path, index=False)
    except Exception as exc:
        raise
    return path


def _collect_fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    """Collect ordered field names across all rows."""
    if not rows:
        return []

    fieldnames = list(rows[0].keys())
    for row in rows[1:]:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    return fieldnames


def _write_csv(rows: list[dict[str, Any]], path: str) -> str:
    """Write flat rows to CSV."""
    if not rows:
        raise ValueError("Cannot export CSV: no rows to write.")

    fieldnames = _collect_fieldnames(rows)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_json(rows: list[dict[str, Any]], path: str) -> str:
    """Write flat rows to JSON."""
    if not rows:
        raise ValueError("Cannot export JSON: no rows to write.")

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=2, default=str, ensure_ascii=False)
    return path


def _write_xlsx(rows: list[dict[str, Any]], path: str) -> str:
    """Write flat rows to XLSX."""
    try:
        import openpyxl
    except ImportError as exc:
        raise ImportError(
            "openpyxl is required for XLSX export. Install it with: pip install openpyxl"
        ) from exc

    if not rows:
        raise ValueError("Cannot export XLSX: no rows to write.")

    fieldnames = _collect_fieldnames(rows)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Descriptors"
    ws.append(fieldnames)

    for row in rows:
        ws.append([row.get(field, "") for field in fieldnames])

    for col_cells in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col_cells)
        ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 2, 60)

    ws.freeze_panes = "A2"
    wb.save(path)
    return path


_WRITERS = {
    "csv": (_write_csv, ".csv"),
    "json": (_write_json, ".json"),
    "xlsx": (_write_xlsx, ".xlsx"),
}


def export_batch(
    pairs: list[tuple],
    output_dir: str = "output",
    base_name: str = "compound",
    formats: list[str] | None = None,
) -> dict[str, str]:
    """
    Export a list of (MoleculeRecord, DescriptorRecord) pairs.

    Parameters
    ----------
    pairs : list of (mol_rec, desc_rec) tuples
    output_dir : directory where files are written
    base_name : file stem, e.g. "benzene"
    formats : subset of ["csv", "json", "xlsx"]; defaults to ["csv"]

    Returns
    -------
    dict mapping format string to output path
    """
    if formats is None:
        formats = ["csv"]

    unknown = [fmt for fmt in formats if fmt not in _WRITERS]
    if unknown:
        raise ValueError(
            f"Unsupported export format(s): {unknown}. Choose from {list(_WRITERS)}."
        )

    os.makedirs(output_dir, exist_ok=True)
    rows = [mol_row(mol_rec, desc_rec) for mol_rec, desc_rec in pairs]

    paths: dict[str, str] = {}
    for fmt in formats:
        writer_fn, ext = _WRITERS[fmt]
        path = os.path.join(output_dir, base_name + ext)
        try:
            writer_fn(rows, path)
            paths[fmt] = path
            logger.debug("Exported %s -> %s", fmt.upper(), path)
        except Exception as exc:
            logger.error("Export to %s failed: %s", fmt.upper(), exc)
            raise

    return paths


__all__ = [
    "mol_row",
    "build_export_row",
    "export_batch",
]