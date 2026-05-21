"""
core/spectra_validation.py
==========================
Validation workflow for spectral predictions against experimental IR and NMR data.

This module compares heuristic predictions from the existing spectra engine with
user-provided experimental peaks. It computes error metrics, coverage, missing
peaks, and exports validation reports to XLSX, Markdown, and publication-ready
plots.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rdkit import Chem
from rdkit.Chem import MolToSmiles

# NOTE: spectra.* and matplotlib/openpyxl imports are deferred to function
# bodies to break the circular import:
#   core/__init__.py -> spectra_validation -> spectra/__init__ -> core.models -> core/__init__.py

logger = logging.getLogger(__name__)

DOMAIN_LABELS = {
    "ir": "IR",
    "proton": "1H NMR",
    "carbon": "13C NMR",
}

DEFAULT_TOLERANCES = {
    "ir": 50.0,
    "proton": 0.5,
    "carbon": 5.0,
}


@dataclass(slots=True)
class SpectraDomainMetrics:
    domain: str
    predicted_count: int = 0
    experimental_count: int = 0
    matched_count: int = 0
    mae: float | None = None
    rmse: float | None = None
    coverage_predicted: float = 0.0
    coverage_experimental: float = 0.0
    missing_experimental: int = 0
    extra_predicted: int = 0
    tolerance: float = 0.0
    details: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "predicted_count": self.predicted_count,
            "experimental_count": self.experimental_count,
            "matched_count": self.matched_count,
            "mae": self.mae,
            "rmse": self.rmse,
            "coverage_predicted": round(self.coverage_predicted, 4),
            "coverage_experimental": round(self.coverage_experimental, 4),
            "missing_experimental": self.missing_experimental,
            "extra_predicted": self.extra_predicted,
            "tolerance": self.tolerance,
            "details": list(self.details),
        }


@dataclass(slots=True)
class SpectraValidationRecord:
    input_smiles: str
    molecule_name: str | None = None
    canonical_smiles: str | None = None
    validation_error: str | None = None
    ir_metrics: SpectraDomainMetrics | None = None
    proton_metrics: SpectraDomainMetrics | None = None
    carbon_metrics: SpectraDomainMetrics | None = None
    success: bool = False

    def to_dict(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "input_smiles": self.input_smiles,
            "molecule_name": self.molecule_name or "",
            "canonical_smiles": self.canonical_smiles or "",
            "success": self.success,
            "validation_error": self.validation_error or "",
        }
        for domain in ("ir", "proton", "carbon"):
            metrics = getattr(self, f"{domain}_metrics")
            if metrics is None:
                row.update(
                    {
                        f"{domain}_predicted_count": 0,
                        f"{domain}_experimental_count": 0,
                        f"{domain}_matched_count": 0,
                        f"{domain}_mae": "",
                        f"{domain}_rmse": "",
                        f"{domain}_coverage_predicted": "",
                        f"{domain}_coverage_experimental": "",
                        f"{domain}_missing_experimental": 0,
                        f"{domain}_extra_predicted": 0,
                        f"{domain}_tolerance": DEFAULT_TOLERANCES[domain],
                    }
                )
            else:
                row.update(
                    {
                        f"{domain}_predicted_count": metrics.predicted_count,
                        f"{domain}_experimental_count": metrics.experimental_count,
                        f"{domain}_matched_count": metrics.matched_count,
                        f"{domain}_mae": metrics.mae if metrics.mae is not None else "",
                        f"{domain}_rmse": metrics.rmse if metrics.rmse is not None else "",
                        f"{domain}_coverage_predicted": metrics.coverage_predicted,
                        f"{domain}_coverage_experimental": metrics.coverage_experimental,
                        f"{domain}_missing_experimental": metrics.missing_experimental,
                        f"{domain}_extra_predicted": metrics.extra_predicted,
                        f"{domain}_tolerance": metrics.tolerance,
                    }
                )
        return row


@dataclass(slots=True)
class SpectraValidationReport:
    records: list[SpectraValidationRecord] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def total(self) -> int:
        return len(self.records)

    def failures(self) -> int:
        return sum(1 for rec in self.records if not rec.success)

    def successes(self) -> int:
        return sum(1 for rec in self.records if rec.success)

    def average_mae(self, domain: str) -> float | None:
        values = [
            met.mae
            for rec in self.records
            if (met := getattr(rec, f"{domain}_metrics")) is not None and met.mae is not None
        ]
        return float(sum(values) / len(values)) if values else None

    def average_rmse(self, domain: str) -> float | None:
        values = [
            met.rmse
            for rec in self.records
            if (met := getattr(rec, f"{domain}_metrics")) is not None and met.rmse is not None
        ]
        return float(sum(values) / len(values)) if values else None

    def average_coverage_predicted(self, domain: str) -> float | None:
        values = [
            met.coverage_predicted
            for rec in self.records
            if (met := getattr(rec, f"{domain}_metrics")) is not None
        ]
        return float(sum(values) / len(values)) if values else None

    def average_coverage_experimental(self, domain: str) -> float | None:
        values = [
            met.coverage_experimental
            for rec in self.records
            if (met := getattr(rec, f"{domain}_metrics")) is not None
        ]
        return float(sum(values) / len(values)) if values else None

    def total_matches(self, domain: str) -> int:
        return sum(
            met.matched_count
            for rec in self.records
            if (met := getattr(rec, f"{domain}_metrics")) is not None
        )

    def failure_rows(self) -> list[dict[str, Any]]:
        return [
            {
                "input_smiles": rec.input_smiles,
                "molecule_name": rec.molecule_name or "",
                "canonical_smiles": rec.canonical_smiles or "",
                "validation_error": rec.validation_error or "",
            }
            for rec in self.records
            if not rec.success
        ]

    def record_rows(self) -> list[dict[str, Any]]:
        return [rec.to_dict() for rec in self.records]

    def benchmark_rows(self) -> list[dict[str, Any]]:
        return [
            {"metric": "total_records", "value": self.total()},
            {"metric": "successes", "value": self.successes()},
            {"metric": "failures", "value": self.failures()},
            {"metric": "average_ir_mae", "value": self.average_mae("ir") if self.average_mae("ir") is not None else ""},
            {"metric": "average_ir_rmse", "value": self.average_rmse("ir") if self.average_rmse("ir") is not None else ""},
            {"metric": "average_ir_coverage_predicted", "value": self.average_coverage_predicted("ir") if self.average_coverage_predicted("ir") is not None else ""},
            {"metric": "average_ir_coverage_experimental", "value": self.average_coverage_experimental("ir") if self.average_coverage_experimental("ir") is not None else ""},
            {"metric": "average_proton_mae", "value": self.average_mae("proton") if self.average_mae("proton") is not None else ""},
            {"metric": "average_proton_rmse", "value": self.average_rmse("proton") if self.average_rmse("proton") is not None else ""},
            {"metric": "average_proton_coverage_predicted", "value": self.average_coverage_predicted("proton") if self.average_coverage_predicted("proton") is not None else ""},
            {"metric": "average_proton_coverage_experimental", "value": self.average_coverage_experimental("proton") if self.average_coverage_experimental("proton") is not None else ""},
            {"metric": "average_carbon_mae", "value": self.average_mae("carbon") if self.average_mae("carbon") is not None else ""},
            {"metric": "average_carbon_rmse", "value": self.average_rmse("carbon") if self.average_rmse("carbon") is not None else ""},
            {"metric": "average_carbon_coverage_predicted", "value": self.average_coverage_predicted("carbon") if self.average_coverage_predicted("carbon") is not None else ""},
            {"metric": "average_carbon_coverage_experimental", "value": self.average_coverage_experimental("carbon") if self.average_coverage_experimental("carbon") is not None else ""},
        ]


def _is_mapping(value: Any) -> bool:
    return hasattr(value, "get") and callable(getattr(value, "get"))


def _safe_float(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("Boolean values are not valid peak values.")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise ValueError("Empty string is not a valid peak value.")
        return float(stripped)
    raise TypeError(f"Cannot convert peak value to float: {type(value).__name__}")


def _midpoint_from_range(value: Any) -> float:
    if isinstance(value, tuple) or isinstance(value, list):
        if len(value) == 2:
            return (_safe_float(value[0]) + _safe_float(value[1])) / 2.0
    raise ValueError(f"Cannot convert range to midpoint: {value!r}")


def _peak_midpoint(peak: Any) -> float:
    if peak is None:
        raise ValueError("Peak value cannot be None.")
    if isinstance(peak, (int, float, str)):
        return _safe_float(peak)
    if _is_mapping(peak):
        for key in ("ppm_mid", "mid_cm", "ppmmid", "midcm", "wavenumber_midpoint", "ppm_midpoint"):
            if key in peak:
                return _safe_float(peak[key])
        for key in ("ppm_range", "wavenumber_range", "range_cm1", "range"):
            if key in peak:
                return _midpoint_from_range(peak[key])
        if "low_cm" in peak and "high_cm" in peak:
            return (_safe_float(peak["low_cm"]) + _safe_float(peak["high_cm"])) / 2.0
        raise ValueError(f"Unsupported peak mapping: {peak!r}")
    if hasattr(peak, "ppm_mid"):
        return float(peak.ppm_mid)
    if hasattr(peak, "mid_cm"):
        return float(peak.mid_cm)
    if hasattr(peak, "ppm_range"):
        return _midpoint_from_range(getattr(peak, "ppm_range"))
    if hasattr(peak, "wavenumber_range"):
        return _midpoint_from_range(getattr(peak, "wavenumber_range"))
    if hasattr(peak, "low_cm") and hasattr(peak, "high_cm"):
        return (float(getattr(peak, "low_cm")) + float(getattr(peak, "high_cm"))) / 2.0
    if hasattr(peak, "low") and hasattr(peak, "high"):
        return (float(getattr(peak, "low")) + float(getattr(peak, "high"))) / 2.0
    raise ValueError(f"Unable to extract midpoint from peak: {peak!r}")


def _normalize_peak_list(peaks: Any) -> list[float]:
    if peaks is None:
        return []
    if not isinstance(peaks, (list, tuple)) or _is_mapping(peaks):
        return [_peak_midpoint(peaks)]
    return [_peak_midpoint(peak) for peak in peaks if peak is not None]


def _compare_peak_lists(predicted: list[float], experimental: list[float], tolerance: float) -> SpectraDomainMetrics:
    predicted_sorted = sorted(predicted)
    experimental_sorted = sorted(experimental)
    details: list[dict[str, Any]] = []
    i = 0
    j = 0
    matched_count = 0
    errors: list[float] = []
    while i < len(predicted_sorted) and j < len(experimental_sorted):
        predicted_value = predicted_sorted[i]
        experimental_value = experimental_sorted[j]
        error = abs(predicted_value - experimental_value)
        if error <= tolerance:
            details.append(
                {
                    "predicted": predicted_value,
                    "experimental": experimental_value,
                    "error": error,
                }
            )
            errors.append(error)
            matched_count += 1
            i += 1
            j += 1
        elif predicted_value < experimental_value:
            i += 1
        else:
            j += 1
    mae = float(sum(errors) / len(errors)) if errors else None
    rmse = float(math.sqrt(sum(e * e for e in errors) / len(errors))) if errors else None
    predicted_count = len(predicted_sorted)
    experimental_count = len(experimental_sorted)
    missing_experimental = experimental_count - matched_count
    extra_predicted = predicted_count - matched_count
    coverage_predicted = float(matched_count / predicted_count) if predicted_count else 0.0
    coverage_experimental = float(matched_count / experimental_count) if experimental_count else 0.0
    return SpectraDomainMetrics(
        domain="",
        predicted_count=predicted_count,
        experimental_count=experimental_count,
        matched_count=matched_count,
        mae=mae,
        rmse=rmse,
        coverage_predicted=coverage_predicted,
        coverage_experimental=coverage_experimental,
        missing_experimental=missing_experimental,
        extra_predicted=extra_predicted,
        tolerance=tolerance,
        details=details,
    )


def _extract_predicted_peaks(prediction: Any, domain: str) -> list[float]:
    if prediction is None:
        return []
    if domain == "ir":
        peaks = getattr(prediction, "bands", None) or getattr(prediction, "peaks", None) or []
    elif domain == "proton":
        peaks = getattr(prediction, "signals", None) or getattr(prediction, "environments", None) or []
    elif domain == "carbon":
        peaks = getattr(prediction, "environments", None) or []
    else:
        raise ValueError(f"Unsupported domain: {domain}")
    return _normalize_peak_list(peaks)


def _extract_experimental_peaks(experimental: Any) -> list[float]:
    return _normalize_peak_list(experimental)


def _build_domain_metrics(prediction: Any, experimental: Any, domain: str, tolerance: float) -> SpectraDomainMetrics:
    metrics = _compare_peak_lists(
        _extract_predicted_peaks(prediction, domain),
        _extract_experimental_peaks(experimental),
        tolerance,
    )
    metrics.domain = domain
    return metrics


def _get_record_value(record: Any, key: str, default: Any = None) -> Any:
    if _is_mapping(record):
        return record.get(key, default)
    return getattr(record, key, default)


def validate_spectra_workflow(
    inputs: list[Any],
    *,
    ir_tolerance: float = DEFAULT_TOLERANCES["ir"],
    proton_tolerance: float = DEFAULT_TOLERANCES["proton"],
    carbon_tolerance: float = DEFAULT_TOLERANCES["carbon"],
) -> SpectraValidationReport:
    report = SpectraValidationReport(metadata={
        "ir_tolerance": ir_tolerance,
        "proton_tolerance": proton_tolerance,
        "carbon_tolerance": carbon_tolerance,
    })
    for entry in inputs:
        smiles = _get_record_value(entry, "smiles")
        molecule_name = _get_record_value(entry, "molecule_name")
        record = SpectraValidationRecord(input_smiles=smiles or "", molecule_name=molecule_name)
        if not isinstance(smiles, str) or not smiles.strip():
            record.validation_error = "SMILES must be a non-empty string."
            report.records.append(record)
            continue
        try:
            rdkit_mol = Chem.MolFromSmiles(smiles)
            if rdkit_mol is None:
                raise ValueError("Invalid SMILES string.")
            Chem.SanitizeMol(rdkit_mol)
            record.canonical_smiles = MolToSmiles(rdkit_mol, canonical=True)
        except Exception as exc:
            record.validation_error = str(exc)
            report.records.append(record)
            continue
        try:
            # Lazy imports here to avoid circular import at module load time
            from spectra.ir_predictor import predict_ir as _predict_ir
            from spectra.proton_nmr import predict_proton_nmr as _predict_proton
            from spectra.carbon_nmr import predict_carbon_nmr as _predict_carbon
            ir_prediction = _predict_ir(rdkit_mol)
            proton_prediction = _predict_proton(rdkit_mol)
            carbon_prediction = _predict_carbon(rdkit_mol)
        except Exception as exc:
            record.validation_error = f"Prediction failure: {exc}"
            report.records.append(record)
            continue
        try:
            record.ir_metrics = _build_domain_metrics(
                ir_prediction,
                _get_record_value(entry, "experimental_ir", []),
                "ir",
                ir_tolerance,
            )
            record.proton_metrics = _build_domain_metrics(
                proton_prediction,
                _get_record_value(entry, "experimental_proton", []),
                "proton",
                proton_tolerance,
            )
            record.carbon_metrics = _build_domain_metrics(
                carbon_prediction,
                _get_record_value(entry, "experimental_carbon", []),
                "carbon",
                carbon_tolerance,
            )
            record.success = True
        except Exception as exc:
            record.validation_error = f"Validation computation failure: {exc}"
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
    report: SpectraValidationReport,
    xlsx_path: str | Path,
    markdown_path: str | Path | None = None,
    plot_dir: str | Path | None = None,
) -> tuple[Path, Path | None, list[Path]]:
    xlsx_target = Path(xlsx_path)
    xlsx_target.parent.mkdir(parents=True, exist_ok=True)
    from openpyxl import Workbook
    wb = Workbook()
    wb.remove(wb.active)
    _write_rows_to_sheet(wb, "summary", report.benchmark_rows())
    _write_rows_to_sheet(wb, "records", report.record_rows())
    _write_rows_to_sheet(wb, "failures", report.failure_rows())
    wb.save(xlsx_target)
    logger.info("Saved spectra validation report to %s", xlsx_target)
    markdown_target = None
    if markdown_path is not None:
        markdown_target = Path(markdown_path)
        markdown_target.parent.mkdir(parents=True, exist_ok=True)
        markdown_target.write_text(build_markdown_report(report), encoding="utf-8")
        logger.info("Saved spectra validation markdown to %s", markdown_target)
    plot_paths: list[Path] = []
    if plot_dir is not None:
        plot_paths = plot_spectra_validation_report(report, plot_dir)
    return xlsx_target, markdown_target, plot_paths


def build_markdown_report(report: SpectraValidationReport) -> str:
    lines: list[str] = ["# Spectra Validation Report", ""]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total records: **{report.total()}**")
    lines.append(f"- Successful records: **{report.successes()}**")
    lines.append(f"- Failed records: **{report.failures()}**")
    lines.append("")
    for domain in ("ir", "proton", "carbon"):
        avg_mae = report.average_mae(domain)
        avg_rmse = report.average_rmse(domain)
        avg_cov_pred = report.average_coverage_predicted(domain)
        avg_cov_exp = report.average_coverage_experimental(domain)
        lines.append(f"### {DOMAIN_LABELS[domain]}")
        lines.append("")
        lines.append(f"- Average MAE: **{avg_mae:.4f}**" if avg_mae is not None else "- Average MAE: **N/A**")
        lines.append(f"- Average RMSE: **{avg_rmse:.4f}**" if avg_rmse is not None else "- Average RMSE: **N/A**")
        lines.append(
            f"- Average predicted coverage: **{avg_cov_pred * 100:.1f}%**" if avg_cov_pred is not None else "- Average predicted coverage: **N/A**"
        )
        lines.append(
            f"- Average experimental coverage: **{avg_cov_exp * 100:.1f}%**" if avg_cov_exp is not None else "- Average experimental coverage: **N/A**"
        )
        lines.append("")
    lines.append("## Record Details")
    lines.append("")
    fieldnames = [
        "input_smiles",
        "molecule_name",
        "canonical_smiles",
        "success",
        "validation_error",
    ]
    for domain in ("ir", "proton", "carbon"):
        fieldnames.extend(
            [
                f"{domain}_predicted_count",
                f"{domain}_experimental_count",
                f"{domain}_matched_count",
                f"{domain}_mae",
                f"{domain}_rmse",
                f"{domain}_coverage_predicted",
                f"{domain}_coverage_experimental",
                f"{domain}_missing_experimental",
                f"{domain}_extra_predicted",
                f"{domain}_tolerance",
            ]
        )
    lines.append("| " + " | ".join(fieldnames) + " |")
    lines.append("| " + " | ".join(["---"] * len(fieldnames)) + " |")
    for row in report.record_rows():
        escaped = [str(row.get(field, "")).replace("|", "\\|") for field in fieldnames]
        lines.append("| " + " | ".join(escaped) + " |")
    if report.failures() > 0:
        lines.append("")
        lines.append("## Failure Details")
        lines.append("")
        lines.append("| input_smiles | molecule_name | canonical_smiles | validation_error |")
        lines.append("| --- | --- | --- | --- |")
        for row in report.failure_rows():
            escaped = [str(row.get(field, "")).replace("|", "\\|") for field in [
                "input_smiles",
                "molecule_name",
                "canonical_smiles",
                "validation_error",
            ]]
            lines.append("| " + " | ".join(escaped) + " |")
    lines.append("")
    return "\n".join(lines)


def plot_spectra_validation_report(report: SpectraValidationReport, plot_dir: str | Path) -> list[Path]:
    import matplotlib.pyplot as plt  # lazy import
    plot_path = Path(plot_dir)
    plot_path.mkdir(parents=True, exist_ok=True)
    file_paths: list[Path] = []
    domains = ["ir", "proton", "carbon"]
    avg_mae = [report.average_mae(domain) or 0.0 for domain in domains]
    avg_rmse = [report.average_rmse(domain) or 0.0 for domain in domains]
    avg_cov_pred = [report.average_coverage_predicted(domain) or 0.0 for domain in domains]
    avg_cov_exp = [report.average_coverage_experimental(domain) or 0.0 for domain in domains]
    counts = [report.total_matches(domain) for domain in domains]
    labels = [DOMAIN_LABELS[d] for d in domains]

    fig, axes = plt.subplots(2, 1, figsize=(10, 10), constrained_layout=True)
    axes[0].bar(labels, avg_mae, color=["#4c72b0", "#55a868", "#c44e52"])
    axes[0].set_title("Average Spectral Validation MAE")
    axes[0].set_ylabel("Error")
    axes[0].grid(axis="y", linestyle="--", alpha=0.35)

    axes[1].bar([f"{label} (pred)" for label in labels], avg_cov_pred, color="#8172b2", alpha=0.8)
    axes[1].bar([f"{label} (exp)" for label in labels], avg_cov_exp, color="#64b5cd", alpha=0.8)
    axes[1].set_title("Average Coverage")
    axes[1].set_ylabel("Coverage")
    axes[1].set_ylim(0.0, 1.0)
    axes[1].grid(axis="y", linestyle="--", alpha=0.35)
    file_paths.append(plot_path / "spectra_validation_summary.png")
    fig.savefig(file_paths[-1], dpi=200)
    plt.close(fig)

    fig2, ax2 = plt.subplots(figsize=(10, 4), constrained_layout=True)
    ax2.bar(labels, counts, color=["#4c72b0", "#55a868", "#c44e52"])
    ax2.set_title("Matched Spectral Peaks by Domain")
    ax2.set_ylabel("Matched peaks")
    ax2.grid(axis="y", linestyle="--", alpha=0.35)
    file_paths.append(plot_path / "spectra_validation_matches.png")
    fig2.savefig(file_paths[-1], dpi=200)
    plt.close(fig2)

    return file_paths


__all__ = [
    "SpectraDomainMetrics",
    "SpectraValidationRecord",
    "SpectraValidationReport",
    "validate_spectra_workflow",
    "export_validation_report",
    "build_markdown_report",
    "plot_spectra_validation_report",
]
