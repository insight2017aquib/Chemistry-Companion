"""
core/docking_validation.py
==========================
Validation workflow for docking preparation.

This module benchmarks Open Babel docking preparation in a batched workflow,
records failure modes, and exports summary reports to XLSX and Markdown.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from rdkit import Chem
from rdkit.Chem import MolToSmiles

from core.docking_preparation import prepare_docking_structure
from core.openbabel_utils import generate_3d_coordinates, optimize_geometry

logger = logging.getLogger(__name__)

SUPPORTED_OUTPUT_FORMATS = {"pdbqt", "pdb", "mol2", "sdf", "xyz", "mol", "smi"}


@dataclass(slots=True)
class DockingValidationRecord:
    input_smiles: str
    canonical_smiles: str | None = None
    validated: bool = False
    validated_error: str | None = None
    generation_time: float | None = None
    optimization_time: float | None = None
    export_time: float | None = None
    output_format: str = "pdbqt"
    success: bool = False
    failure_stage: str | None = None
    failure_message: str | None = None
    initial_atoms: int | None = None
    initial_heavy_atoms: int | None = None
    conformer_count: int | None = None
    output_size: int | None = None
    pdbqt_compatible: bool | None = None


@dataclass(slots=True)
class DockingValidationReport:
    records: list[DockingValidationRecord] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def total(self) -> int:
        return len(self.records)

    def successes(self) -> int:
        return sum(1 for rec in self.records if rec.success)

    def failures(self) -> int:
        return sum(1 for rec in self.records if not rec.success)

    def success_rate(self) -> float:
        total = self.total()
        return 100.0 * self.successes() / total if total else 0.0

    def average_generation_time(self) -> float | None:
        times = [rec.generation_time for rec in self.records if rec.generation_time is not None]
        return float(sum(times)) / len(times) if times else None

    def average_optimization_time(self) -> float | None:
        times = [rec.optimization_time for rec in self.records if rec.optimization_time is not None]
        return float(sum(times)) / len(times) if times else None

    def average_export_time(self) -> float | None:
        times = [rec.export_time for rec in self.records if rec.export_time is not None]
        return float(sum(times)) / len(times) if times else None

    def failure_breakdown(self) -> dict[str, int]:
        breakdown: dict[str, int] = {}
        for rec in self.records:
            if not rec.success:
                key = rec.failure_stage or "unknown"
                breakdown[key] = breakdown.get(key, 0) + 1
        return breakdown

    def benchmark_rows(self) -> list[dict[str, Any]]:
        return [
            {
                "metric": "total_inputs",
                "value": self.total(),
            },
            {
                "metric": "successes",
                "value": self.successes(),
            },
            {
                "metric": "failures",
                "value": self.failures(),
            },
            {
                "metric": "success_rate_percent",
                "value": round(self.success_rate(), 2),
            },
            {
                "metric": "average_3d_generation_time_s",
                "value": round(self.average_generation_time() or 0.0, 4),
            },
            {
                "metric": "average_optimization_time_s",
                "value": round(self.average_optimization_time() or 0.0, 4),
            },
            {
                "metric": "average_export_time_s",
                "value": round(self.average_export_time() or 0.0, 4),
            },
        ]

    def failure_rows(self) -> list[dict[str, Any]]:
        return [
            {
                "input_smiles": rec.input_smiles,
                "canonical_smiles": rec.canonical_smiles or "",
                "failure_stage": rec.failure_stage or "",
                "failure_message": rec.failure_message or "",
            }
            for rec in self.records
            if not rec.success
        ]

    def record_rows(self) -> list[dict[str, Any]]:
        return [
            {
                "input_smiles": rec.input_smiles,
                "canonical_smiles": rec.canonical_smiles or "",
                "validated": rec.validated,
                "validated_error": rec.validated_error or "",
                "generation_time_s": rec.generation_time,
                "optimization_time_s": rec.optimization_time,
                "export_time_s": rec.export_time,
                "output_format": rec.output_format,
                "success": rec.success,
                "failure_stage": rec.failure_stage or "",
                "failure_message": rec.failure_message or "",
                "initial_atoms": rec.initial_atoms,
                "initial_heavy_atoms": rec.initial_heavy_atoms,
                "conformer_count": rec.conformer_count,
                "output_size_bytes": rec.output_size,
                "pdbqt_compatible": rec.pdbqt_compatible,
            }
            for rec in self.records
        ]


def _ensure_output_format(fmt: str) -> str:
    normalized = fmt.strip().lower()
    if normalized not in SUPPORTED_OUTPUT_FORMATS:
        raise ValueError(f"Unsupported output format: {fmt}")
    return normalized


def validate_docking_workflow(
    smiles_inputs: list[str],
    *,
    output_format: str = "pdbqt",
    optimization_method: str = "uff",
    optimization_steps: int = 250,
    add_hydrogens: bool = True,
) -> DockingValidationReport:
    output_format = _ensure_output_format(output_format)
    report = DockingValidationReport(metadata={"output_format": output_format})

    for smiles in smiles_inputs:
        record = DockingValidationRecord(input_smiles=smiles, output_format=output_format)
        try:
            if not isinstance(smiles, str) or not smiles.strip():
                raise ValueError("SMILES must be a non-empty string.")
            rdkit_mol = Chem.MolFromSmiles(smiles)
            if rdkit_mol is None:
                raise ValueError("Invalid SMILES string.")
            Chem.SanitizeMol(rdkit_mol)
            record.canonical_smiles = MolToSmiles(rdkit_mol, canonical=True)
            record.validated = True
            record.initial_atoms = rdkit_mol.GetNumAtoms()
            record.initial_heavy_atoms = rdkit_mol.GetNumHeavyAtoms()
        except Exception as exc:
            record.failure_stage = "validation"
            record.failure_message = str(exc)
            record.validated_error = str(exc)
            report.records.append(record)
            continue

        try:
            start = time.perf_counter()
            obmol = generate_3d_coordinates(record.canonical_smiles, input_format="smi")
            record.generation_time = time.perf_counter() - start
            record.conformer_count = int(obmol.OBMol.NumConformers())
            if record.conformer_count == 0:
                raise RuntimeError("No conformer generated.")
        except Exception as exc:
            record.failure_stage = "3d_generation"
            record.failure_message = str(exc)
            report.records.append(record)
            continue

        try:
            start = time.perf_counter()
            optimized = optimize_geometry(
                obmol,
                method=optimization_method,
                steps=optimization_steps,
            )
            record.optimization_time = time.perf_counter() - start
            record.conformer_count = int(optimized.OBMol.NumConformers())
        except Exception as exc:
            record.failure_stage = "optimization"
            record.failure_message = str(exc)
            report.records.append(record)
            continue

        try:
            start = time.perf_counter()
            structure = optimized.write(output_format)
            record.export_time = time.perf_counter() - start
            record.output_size = len(structure or "")
            if not structure or not structure.strip():
                raise RuntimeError("Exported docking file is empty.")
            if output_format == "pdbqt":
                record.pdbqt_compatible = (
                    "ATOM" in structure or "HETATM" in structure
                ) and "REMARK" in structure
            else:
                record.pdbqt_compatible = None
            record.success = True
        except Exception as exc:
            record.failure_stage = "export"
            record.failure_message = str(exc)
        report.records.append(record)

    return report


def _write_rows_to_sheet(wb: Workbook, sheet_name: str, rows: list[dict[str, Any]]):
    worksheet = wb.create_sheet(sheet_name)
    if not rows:
        worksheet.append(["message"])
        worksheet.append(["No data available."])
        return

    fieldnames = list(rows[0].keys())
    worksheet.append(fieldnames)
    for row in rows:
        worksheet.append([row.get(key, "") for key in fieldnames])

    for column_cells in worksheet.columns:
        max_length = max(len(str(cell.value or "")) for cell in column_cells)
        worksheet.column_dimensions[column_cells[0].column_letter].width = min(max_length + 2, 60)
    worksheet.freeze_panes = "A2"


def export_validation_report(
    report: DockingValidationReport,
    xlsx_path: str | Path,
    markdown_path: str | Path | None = None,
) -> tuple[Path, Path | None]:
    xlsx_target = Path(xlsx_path)
    xlsx_target.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    wb.remove(wb.active)
    _write_rows_to_sheet(wb, "summary", report.benchmark_rows())
    _write_rows_to_sheet(wb, "records", report.record_rows())
    _write_rows_to_sheet(wb, "failures", report.failure_rows())
    wb.save(xlsx_target)
    logger.info("Saved docking validation report to %s", xlsx_target)

    markdown_target = None
    if markdown_path is not None:
        markdown_target = Path(markdown_path)
        markdown_target.parent.mkdir(parents=True, exist_ok=True)
        markdown_target.write_text(build_markdown_report(report), encoding="utf-8")
        logger.info("Saved docking validation markdown to %s", markdown_target)

    return xlsx_target, markdown_target


def build_markdown_report(report: DockingValidationReport) -> str:
    lines: list[str] = []
    lines.append("# Docking Preparation Validation Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total inputs: **{report.total()}**")
    lines.append(f"- Successful preparations: **{report.successes()}**")
    lines.append(f"- Failed preparations: **{report.failures()}**")
    lines.append(f"- Success rate: **{report.success_rate():.2f}%**")
    lines.append(
        f"- Average 3D generation time: **{report.average_generation_time() or 0:.4f}s**"
    )
    lines.append(
        f"- Average optimization time: **{report.average_optimization_time() or 0:.4f}s**"
    )
    lines.append(f"- Average export time: **{report.average_export_time() or 0:.4f}s**")
    lines.append("")

    lines.append("## Failure Breakdown")
    lines.append("")
    if report.failures() == 0:
        lines.append("All inputs were prepared successfully.")
    else:
        for stage, count in report.failure_breakdown().items():
            lines.append(f"- **{stage}**: {count}")
    lines.append("")

    lines.append("## Detail Table")
    lines.append("")
    fieldnames = [
        "input_smiles",
        "canonical_smiles",
        "validated",
        "success",
        "failure_stage",
        "failure_message",
        "generation_time_s",
        "optimization_time_s",
        "export_time_s",
        "conformer_count",
        "output_size_bytes",
        "pdbqt_compatible",
    ]
    lines.append("| " + " | ".join(fieldnames) + " |")
    lines.append("| " + " | ".join(["---"] * len(fieldnames)) + " |")
    for row in report.record_rows():
        escaped = [str(row.get(field, "")).replace("|", "\\|") for field in fieldnames]
        lines.append("| " + " | ".join(escaped) + " |")
    lines.append("")

    failure_rows = report.failure_rows()
    if failure_rows:
        lines.append("## Failure Analysis")
        lines.append("")
        lines.append("| input_smiles | canonical_smiles | failure_stage | failure_message |")
        lines.append("| --- | --- | --- | --- |")
        for row in failure_rows:
            escaped = [str(row.get(field, "")).replace("|", "\\|") for field in [
                "input_smiles",
                "canonical_smiles",
                "failure_stage",
                "failure_message",
            ]]
            lines.append("| " + " | ".join(escaped) + " |")
        lines.append("")

    return "\n".join(lines)


__all__ = [
    "DockingValidationRecord",
    "DockingValidationReport",
    "validate_docking_workflow",
    "export_validation_report",
    "build_markdown_report",
]
