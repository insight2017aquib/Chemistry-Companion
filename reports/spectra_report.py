"""
chemistry_companion/reports/spectra_report.py
=============================================

Combined spectral report builder for Chemistry Companion.

Features
--------
- Combined heuristic reporting for:
  - IR predictions
  - 1H NMR predictions
  - 13C NMR predictions
  - Functional group analysis
- Export to JSON, CSV, and Markdown
- Batch reporting
- Lazy imports to tolerate module evolution
- Structured dataclass outputs
- Logging, type hints, and error handling

Important
---------
All spectral predictions handled by this module are heuristic/approximate.
This module does NOT claim quantum accuracy, solvent correction, or
experimentally validated assignment quality.
"""

from __future__ import annotations

import csv
import json
import logging
from collections import Counter
from dataclasses import asdict, dataclass, field, is_dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from rdkit import Chem

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

InputType = Union[str, Chem.Mol]
BatchInputType = Union[
    str,
    Chem.Mol,
    Dict[str, Any],
]

HEURISTIC_NOTE = (
    "HEURISTIC ONLY — combined spectral report built from approximate rule-based predictions."
)


@dataclass
class FunctionalGroupAnalysis:
    """Structured functional-group summary."""

    keys: List[str] = field(default_factory=list)
    names: List[str] = field(default_factory=list)
    counts: Dict[str, int] = field(default_factory=dict)
    source: str = "unknown"
    is_heuristic: bool = True
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Return serializable dictionary."""
        return {
            "keys": list(self.keys),
            "names": list(self.names),
            "counts": dict(self.counts),
            "source": self.source,
            "is_heuristic": self.is_heuristic,
            "warnings": list(self.warnings),
        }


@dataclass
class SpectraReport:
    """Combined per-molecule spectral report."""

    molecule_id: str
    input_value: str
    input_format: str
    canonical_smiles: str
    molecule_name: Optional[str] = None
    ir: Dict[str, Any] = field(default_factory=dict)
    proton_nmr: Dict[str, Any] = field(default_factory=dict)
    carbon_nmr: Dict[str, Any] = field(default_factory=dict)
    functional_groups: FunctionalGroupAnalysis = field(default_factory=FunctionalGroupAnalysis)
    warnings: List[str] = field(default_factory=list)
    is_heuristic: bool = True
    heuristic_note: str = HEURISTIC_NOTE

    def to_dict(self) -> Dict[str, Any]:
        """Return serializable dictionary."""
        return {
            "molecule_id": self.molecule_id,
            "molecule_name": self.molecule_name,
            "input_value": self.input_value,
            "input_format": self.input_format,
            "canonical_smiles": self.canonical_smiles,
            "ir": self.ir,
            "proton_nmr": self.proton_nmr,
            "carbon_nmr": self.carbon_nmr,
            "functional_groups": self.functional_groups.to_dict(),
            "warnings": list(self.warnings),
            "is_heuristic": self.is_heuristic,
            "heuristic_note": self.heuristic_note,
        }

    def to_markdown(self) -> str:
        """Render a single report as Markdown."""
        title = self.molecule_name or self.molecule_id
        fg_names = ", ".join(self.functional_groups.names) or "None detected"

        lines: List[str] = [
            f"# Spectral Report: {title}",
            "",
            f"- **Molecule ID:** {self.molecule_id}",
            f"- **Input format:** {self.input_format}",
            f"- **Input value:** `{self.input_value}`",
            f"- **Canonical SMILES:** `{self.canonical_smiles}`",
            f"- **Heuristic note:** {self.heuristic_note}",
            "",
            "## Functional Groups",
            "",
            f"- **Detected groups:** {fg_names}",
            f"- **Source:** {self.functional_groups.source}",
        ]

        if self.functional_groups.counts:
            lines.extend(
                [
                    "",
                    "| Functional Group | Count |",
                    "|---|---:|",
                ]
            )
            for name, count in sorted(self.functional_groups.counts.items()):
                lines.append(f"| {name} | {count} |")

        lines.extend(
            [
                "",
                "## IR",
                "",
                _markdown_for_section(self.ir, "bands", ("label", "low_cm", "high_cm", "intensity")),
                "",
                "## 1H NMR",
                "",
                _markdown_for_section(
                    self.proton_nmr,
                    "signals",
                    ("label", "ppm_range", "multiplicity", "integration"),
                ),
                "",
                "## 13C NMR",
                "",
                _markdown_for_section(
                    self.carbon_nmr,
                    "environments",
                    ("label", "ppm_range", "carbon_count", "annotation"),
                ),
            ]
        )

        if self.warnings:
            lines.extend(["", "## Warnings", ""])
            for warning in self.warnings:
                lines.append(f"- {warning}")

        return "\n".join(lines)


@dataclass
class BatchSpectraReport:
    """Batch collection of spectral reports."""

    reports: List[SpectraReport] = field(default_factory=list)
    failed_items: List[Dict[str, str]] = field(default_factory=list)
    is_heuristic: bool = True
    heuristic_note: str = HEURISTIC_NOTE

    @property
    def n_reports(self) -> int:
        """Number of successful reports."""
        return len(self.reports)

    @property
    def n_failed(self) -> int:
        """Number of failed items."""
        return len(self.failed_items)

    def to_dict(self) -> Dict[str, Any]:
        """Return serializable dictionary."""
        return {
            "reports": [report.to_dict() for report in self.reports],
            "failed_items": list(self.failed_items),
            "n_reports": self.n_reports,
            "n_failed": self.n_failed,
            "is_heuristic": self.is_heuristic,
            "heuristic_note": self.heuristic_note,
        }

    def to_markdown(self) -> str:
        """Render batch report as Markdown."""
        lines = [
            "# Batch Spectral Report",
            "",
            f"- **Successful reports:** {self.n_reports}",
            f"- **Failed items:** {self.n_failed}",
            f"- **Heuristic note:** {self.heuristic_note}",
            "",
        ]

        for report in self.reports:
            lines.append(report.to_markdown())
            lines.append("")
            lines.append("---")
            lines.append("")

        if self.failed_items:
            lines.extend(["## Failed Items", ""])
            lines.extend(
                f"- `{item.get('input', '')}`: {item.get('error', 'Unknown error')}"
                for item in self.failed_items
            )

        return "\n".join(lines).rstrip()


class SpectraReportBuilder:
    """
    Build combined spectral reports from existing predictor modules.

    Parameters
    ----------
    ir_predictor:
        Optional callable or predictor object for IR prediction.
    proton_predictor:
        Optional callable or predictor object for 1H NMR prediction.
    carbon_predictor:
        Optional callable or predictor object for 13C NMR prediction.
    fg_detector:
        Optional callable for functional-group detection fallback.
    """

    def __init__(
        self,
        ir_predictor: Optional[Any] = None,
        proton_predictor: Optional[Any] = None,
        carbon_predictor: Optional[Any] = None,
        fg_detector: Optional[Callable[[Chem.Mol], Any]] = None,
    ) -> None:
        self._ir_predictor = ir_predictor
        self._proton_predictor = proton_predictor
        self._carbon_predictor = carbon_predictor
        self._fg_detector = fg_detector

    def build_report(
        self,
        mol_or_smiles: InputType,
        molecule_name: Optional[str] = None,
        molecule_id: Optional[str] = None,
    ) -> SpectraReport:
        """
        Build a combined report for one molecule.

        Raises
        ------
        ValueError
            If the input cannot be parsed into a valid RDKit molecule.
        """
        mol, canonical_smiles, input_value, input_format = _normalise_input(mol_or_smiles)
        warnings: List[str] = []
        mol_id = molecule_id or molecule_name or canonical_smiles

        ir_prediction = self._run_ir(mol, canonical_smiles, warnings)
        proton_prediction = self._run_proton(mol, canonical_smiles, warnings)
        carbon_prediction = self._run_carbon(mol, canonical_smiles, warnings)
        fg_analysis = self._extract_functional_groups(mol, ir_prediction, warnings)

        return SpectraReport(
            molecule_id=mol_id,
            molecule_name=molecule_name,
            input_value=input_value,
            input_format=input_format,
            canonical_smiles=canonical_smiles,
            ir=_safe_to_dict(ir_prediction),
            proton_nmr=_safe_to_dict(proton_prediction),
            carbon_nmr=_safe_to_dict(carbon_prediction),
            functional_groups=fg_analysis,
            warnings=warnings,
        )

    def build_batch(
        self,
        items: Sequence[BatchInputType],
    ) -> BatchSpectraReport:
        """
        Build reports for multiple inputs.

        Supported item formats
        ----------------------
        - "CCO"
        - RDKit Mol
        - {"input": "CCO", "name": "ethanol", "id": "mol-1"}
        """
        reports: List[SpectraReport] = []
        failed_items: List[Dict[str, str]] = []

        for idx, item in enumerate(items, start=1):
            try:
                parsed = _parse_batch_item(item, idx)
                report = self.build_report(
                    parsed["input"],
                    molecule_name=parsed.get("name"),
                    molecule_id=parsed.get("id"),
                )
                reports.append(report)
            except Exception as exc:
                logger.exception("Failed to build batch report for item %s", idx)
                failed_items.append(
                    {
                        "index": str(idx),
                        "input": _short_input_repr(item),
                        "error": str(exc),
                    }
                )

        return BatchSpectraReport(reports=reports, failed_items=failed_items)

    def export_json(
        self,
        report: Union[SpectraReport, BatchSpectraReport],
        output_path: Union[str, Path],
        indent: int = 2,
    ) -> Path:
        """Export report object to JSON."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = report.to_dict()
        path.write_text(json.dumps(data, indent=indent, ensure_ascii=False), encoding="utf-8")
        logger.info("JSON report written to %s", path)
        return path

    def export_csv(
        self,
        report: Union[SpectraReport, BatchSpectraReport],
        output_path: Union[str, Path],
    ) -> Path:
        """Export report object to flattened CSV."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(report, SpectraReport):
            rows = [self._flatten_report(report)]
        else:
            rows = [self._flatten_report(r) for r in report.reports]

        if not rows:
            rows = [self._flatten_report(_empty_report())]

        fieldnames = list(rows[0].keys())
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        logger.info("CSV report written to %s", path)
        return path

    def export_markdown(
        self,
        report: Union[SpectraReport, BatchSpectraReport],
        output_path: Union[str, Path],
    ) -> Path:
        """Export report object to Markdown."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        markdown = report.to_markdown()
        path.write_text(markdown, encoding="utf-8")
        logger.info("Markdown report written to %s", path)
        return path

    def _run_ir(
        self,
        mol: Chem.Mol,
        smiles: str,
        warnings: List[str],
    ) -> Any:
        predictor = self._resolve_ir_predictor()
        if predictor is None:
            warnings.append("IR predictor unavailable; IR section omitted.")
            return {
                "available": False,
                "error": "IR predictor unavailable",
                "is_heuristic": True,
            }

        try:
            return _invoke_predictor(predictor, mol, smiles)
        except Exception as exc:
            logger.exception("IR prediction failed")
            warnings.append(f"IR prediction failed: {exc}")
            return {
                "available": False,
                "error": str(exc),
                "is_heuristic": True,
            }

    def _run_proton(
        self,
        mol: Chem.Mol,
        smiles: str,
        warnings: List[str],
    ) -> Any:
        predictor = self._resolve_proton_predictor()
        if predictor is None:
            warnings.append("1H NMR predictor unavailable; proton section omitted.")
            return {
                "available": False,
                "error": "1H NMR predictor unavailable",
                "is_heuristic": True,
            }

        try:
            return _invoke_predictor(predictor, mol, smiles)
        except Exception as exc:
            logger.exception("1H NMR prediction failed")
            warnings.append(f"1H NMR prediction failed: {exc}")
            return {
                "available": False,
                "error": str(exc),
                "is_heuristic": True,
            }

    def _run_carbon(
        self,
        mol: Chem.Mol,
        smiles: str,
        warnings: List[str],
    ) -> Any:
        predictor = self._resolve_carbon_predictor()
        if predictor is None:
            warnings.append("13C NMR predictor unavailable; carbon section omitted.")
            return {
                "available": False,
                "error": "13C NMR predictor unavailable",
                "is_heuristic": True,
            }

        try:
            return _invoke_predictor(predictor, mol, smiles)
        except Exception as exc:
            logger.exception("13C NMR prediction failed")
            warnings.append(f"13C NMR prediction failed: {exc}")
            return {
                "available": False,
                "error": str(exc),
                "is_heuristic": True,
            }

    def _extract_functional_groups(
        self,
        mol: Chem.Mol,
        ir_prediction: Any,
        warnings: List[str],
    ) -> FunctionalGroupAnalysis:
        """
        Extract functional groups.

        Priority
        --------
        1. Use IR prediction metadata if available.
        2. Use explicit functional-group detector if provided.
        3. Return empty analysis with a warning.
        """
        try:
            if hasattr(ir_prediction, "fg_names") or hasattr(ir_prediction, "fg_keys"):
                names = list(getattr(ir_prediction, "fg_names", []) or [])
                keys = list(getattr(ir_prediction, "fg_keys", []) or [])
                counts = dict(Counter(names or keys))
                return FunctionalGroupAnalysis(
                    keys=keys,
                    names=names,
                    counts=counts,
                    source="ir_prediction",
                    is_heuristic=True,
                )

            if isinstance(ir_prediction, dict):
                names = list(ir_prediction.get("fg_names", []) or [])
                keys = list(ir_prediction.get("fg_keys", []) or [])
                counts = dict(Counter(names or keys))
                if names or keys:
                    return FunctionalGroupAnalysis(
                        keys=keys,
                        names=names,
                        counts=counts,
                        source="ir_prediction",
                        is_heuristic=True,
                    )

            detector = self._resolve_fg_detector()
            if detector is not None:
                result = detector(mol)
                parsed = _parse_fg_detection(result)
                parsed.source = "functional_group_detector"
                return parsed
        except Exception as exc:
            logger.exception("Functional-group extraction failed")
            warnings.append(f"Functional-group extraction failed: {exc}")

        warnings.append("Functional-group analysis unavailable or empty.")
        return FunctionalGroupAnalysis(
            source="unavailable",
            warnings=["No functional-group metadata available."],
        )

    def _resolve_ir_predictor(self) -> Optional[Any]:
        if self._ir_predictor is not None:
            return self._ir_predictor
        try:
            module = import_module("spectra.ir_predictor")
            if hasattr(module, "predict_ir"):
                return getattr(module, "predict_ir")
            if hasattr(module, "IRPredictor"):
                return module.IRPredictor()
        except Exception as exc:
            logger.warning("Could not import IR predictor: %s", exc)
        return None

    def _resolve_proton_predictor(self) -> Optional[Any]:
        if self._proton_predictor is not None:
            return self._proton_predictor
        try:
            module = import_module("spectra.proton_nmr")
            if hasattr(module, "predict_proton_nmr"):
                return getattr(module, "predict_proton_nmr")
            if hasattr(module, "predict_from_smiles"):
                return getattr(module, "predict_from_smiles")
            if hasattr(module, "ProtonNMRPredictor"):
                return module.ProtonNMRPredictor()
        except Exception as exc:
            logger.warning("Could not import proton NMR predictor: %s", exc)
        return None

    def _resolve_carbon_predictor(self) -> Optional[Any]:
        if self._carbon_predictor is not None:
            return self._carbon_predictor
        try:
            module = import_module("spectra.carbon_nmr")
            if hasattr(module, "predict_carbon_nmr"):
                return getattr(module, "predict_carbon_nmr")
            if hasattr(module, "predict_from_smiles"):
                return getattr(module, "predict_from_smiles")
            if hasattr(module, "CarbonNMRPredictor"):
                return module.CarbonNMRPredictor()
        except Exception as exc:
            logger.warning("Could not import carbon NMR predictor: %s", exc)
        return None

    def _resolve_fg_detector(self) -> Optional[Callable[[Chem.Mol], Any]]:
        if self._fg_detector is not None:
            return self._fg_detector
        try:
            module = import_module("spectra.functional_group_detector")
            if hasattr(module, "FunctionalGroupDetector"):
                detector = module.FunctionalGroupDetector()
                if hasattr(detector, "detect"):
                    return detector.detect
        except Exception as exc:
            logger.debug("Could not import functional_group_detector: %s", exc)

        try:
            module = import_module("core.descriptor_utils")
            if hasattr(module, "detect_functional_groups"):
                return getattr(module, "detect_functional_groups")
        except Exception as exc:
            logger.debug("Could not import core.descriptor_utils.detect_functional_groups: %s", exc)

        return None

    def _flatten_report(self, report: SpectraReport) -> Dict[str, Any]:
        fg_names = report.functional_groups.names
        ir_bands = _extract_items(report.ir, "bands")
        proton_signals = _extract_items(report.proton_nmr, "signals")
        carbon_envs = _extract_items(report.carbon_nmr, "environments")

        return {
            "molecule_id": report.molecule_id,
            "molecule_name": report.molecule_name or "",
            "input_format": report.input_format,
            "input_value": report.input_value,
            "canonical_smiles": report.canonical_smiles,
            "functional_groups": "; ".join(fg_names),
            "functional_group_source": report.functional_groups.source,
            "ir_band_count": len(ir_bands),
            "ir_summary": _summarise_ir_items(ir_bands),
            "proton_signal_count": len(proton_signals),
            "proton_summary": _summarise_proton_items(proton_signals),
            "carbon_signal_count": len(carbon_envs),
            "carbon_summary": _summarise_carbon_items(carbon_envs),
            "warning_count": len(report.warnings),
            "warnings": " | ".join(report.warnings),
            "is_heuristic": report.is_heuristic,
        }


def build_spectra_report(
    mol_or_smiles: InputType,
    molecule_name: Optional[str] = None,
    molecule_id: Optional[str] = None,
    ir_predictor: Optional[Any] = None,
    proton_predictor: Optional[Any] = None,
    carbon_predictor: Optional[Any] = None,
    fg_detector: Optional[Callable[[Chem.Mol], Any]] = None,
) -> SpectraReport:
    """Convenience wrapper for single-report generation."""
    builder = SpectraReportBuilder(
        ir_predictor=ir_predictor,
        proton_predictor=proton_predictor,
        carbon_predictor=carbon_predictor,
        fg_detector=fg_detector,
    )
    return builder.build_report(
        mol_or_smiles=mol_or_smiles,
        molecule_name=molecule_name,
        molecule_id=molecule_id,
    )


def build_batch_spectra_reports(
    items: Sequence[BatchInputType],
    ir_predictor: Optional[Any] = None,
    proton_predictor: Optional[Any] = None,
    carbon_predictor: Optional[Any] = None,
    fg_detector: Optional[Callable[[Chem.Mol], Any]] = None,
) -> BatchSpectraReport:
    """Convenience wrapper for batch report generation."""
    builder = SpectraReportBuilder(
        ir_predictor=ir_predictor,
        proton_predictor=proton_predictor,
        carbon_predictor=carbon_predictor,
        fg_detector=fg_detector,
    )
    return builder.build_batch(items)


def export_json_report(
    report: Union[SpectraReport, BatchSpectraReport],
    output_path: Union[str, Path],
    indent: int = 2,
) -> Path:
    """Export JSON using default builder."""
    return SpectraReportBuilder().export_json(report, output_path, indent=indent)


def export_csv_report(
    report: Union[SpectraReport, BatchSpectraReport],
    output_path: Union[str, Path],
) -> Path:
    """Export CSV using default builder."""
    return SpectraReportBuilder().export_csv(report, output_path)


def export_markdown_report(
    report: Union[SpectraReport, BatchSpectraReport],
    output_path: Union[str, Path],
) -> Path:
    """Export Markdown using default builder."""
    return SpectraReportBuilder().export_markdown(report, output_path)


def _normalise_input(mol_or_smiles: InputType) -> Tuple[Chem.Mol, str, str, str]:
    """Convert supported input into (mol, canonical_smiles, input_value, input_format)."""
    if isinstance(mol_or_smiles, str):
        smiles = mol_or_smiles.strip()
        if not smiles:
            raise ValueError("Input SMILES string is empty.")
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise ValueError(f"Could not parse SMILES: {mol_or_smiles}")
        canonical_smiles = Chem.MolToSmiles(mol, isomericSmiles=True)
        return mol, canonical_smiles, smiles, "smiles"

    if mol_or_smiles is None:
        raise ValueError("Input molecule is None.")

    if hasattr(mol_or_smiles, "GetNumAtoms"):
        canonical_smiles = Chem.MolToSmiles(mol_or_smiles, isomericSmiles=True)
        return mol_or_smiles, canonical_smiles, canonical_smiles, "mol"

    raise TypeError(f"Unsupported input type: {type(mol_or_smiles).__name__}")


def _invoke_predictor(predictor: Any, mol: Chem.Mol, smiles: str) -> Any:
    """
    Call predictor robustly across function/object styles.

    Supported patterns
    ------------------
    - callable(smiles)
    - callable(mol)
    - predictor.predict(mol)
    - predictor.predict_from_smiles(smiles)
    """
    if hasattr(predictor, "predict"):
        return predictor.predict(mol)

    if hasattr(predictor, "predict_from_smiles"):
        return predictor.predict_from_smiles(smiles)

    if callable(predictor):
        try:
            return predictor(mol)
        except Exception:
            return predictor(smiles)

    raise TypeError("Predictor is not callable and has no supported prediction method.")


def _safe_to_dict(obj: Any) -> Dict[str, Any]:
    """Convert prediction object to dict when possible."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "to_dict"):
        try:
            data = obj.to_dict()
            if isinstance(data, dict):
                return data
        except Exception:
            logger.debug("to_dict() failed for %s", type(obj).__name__)
    if is_dataclass(obj):
        try:
            data = asdict(obj)
            if isinstance(data, dict):
                return data
        except Exception:
            logger.debug("asdict() failed for %s", type(obj).__name__)
    return {"repr": repr(obj), "is_heuristic": True}


def _parse_fg_detection(result: Any) -> FunctionalGroupAnalysis:
    """Parse a variety of possible functional-group detector outputs."""
    if result is None:
        return FunctionalGroupAnalysis(source="functional_group_detector")

    if isinstance(result, FunctionalGroupAnalysis):
        return result

    if isinstance(result, dict):
        keys = list(result.get("keys", []) or [])
        names = list(result.get("names", []) or [])
        counts = dict(result.get("counts", {}) or Counter(names or keys))
        return FunctionalGroupAnalysis(
            keys=keys,
            names=names,
            counts=counts,
            source=result.get("source", "functional_group_detector"),
            warnings=list(result.get("warnings", []) or []),
        )

    keys = list(getattr(result, "keys", []) or [])
    names = list(getattr(result, "names", []) or [])
    counts = dict(getattr(result, "counts", {}) or Counter(names or keys))

    matches = getattr(result, "matches", None)
    if matches and not names:
        names = [getattr(match, "name", str(match)) for match in matches]
        counts = dict(Counter(names))

    return FunctionalGroupAnalysis(
        keys=keys,
        names=names,
        counts=counts,
        source="functional_group_detector",
    )


def _parse_batch_item(item: BatchInputType, idx: int) -> Dict[str, Any]:
    """Normalize batch item into a dict."""
    if isinstance(item, dict):
        if "input" not in item:
            raise KeyError("Batch item dict must contain an 'input' key.")
        return {
            "input": item["input"],
            "name": item.get("name"),
            "id": item.get("id", f"mol-{idx}"),
        }
    return {"input": item, "name": None, "id": f"mol-{idx}"}


def _short_input_repr(item: Any, max_len: int = 60) -> str:
    """Compact text representation for batch error logs."""
    text = str(item)
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def _extract_items(section: Dict[str, Any], key: str) -> List[Dict[str, Any]]:
    """Extract list-like items from a report section dict."""
    if not isinstance(section, dict):
        return []
    items = section.get(key, [])
    return items if isinstance(items, list) else []


def _summarise_ir_items(items: List[Dict[str, Any]], limit: int = 3) -> str:
    if not items:
        return ""
    parts = []
    for item in items[:limit]:
        label = item.get("label", "band")
        lo = item.get("low_cm")
        hi = item.get("high_cm")
        if lo is not None and hi is not None:
            parts.append(f"{label} ({lo}-{hi} cm^-1)")
        else:
            parts.append(str(label))
    return "; ".join(parts)


def _summarise_proton_items(items: List[Dict[str, Any]], limit: int = 3) -> str:
    if not items:
        return ""
    parts = []
    for item in items[:limit]:
        label = item.get("label", "signal")
        ppm_range = item.get("ppm_range")
        multiplicity = item.get("multiplicity", "")
        if isinstance(ppm_range, (list, tuple)) and len(ppm_range) == 2:
            parts.append(f"{label} ({ppm_range[0]}-{ppm_range[1]} ppm, {multiplicity})")
        else:
            parts.append(str(label))
    return "; ".join(parts)


def _summarise_carbon_items(items: List[Dict[str, Any]], limit: int = 3) -> str:
    if not items:
        return ""
    parts = []
    for item in items[:limit]:
        label = item.get("label", "environment")
        ppm_range = item.get("ppm_range")
        if isinstance(ppm_range, (list, tuple)) and len(ppm_range) == 2:
            parts.append(f"{label} ({ppm_range[0]}-{ppm_range[1]} ppm)")
        else:
            parts.append(str(label))
    return "; ".join(parts)


def _markdown_for_section(
    section: Dict[str, Any],
    key: str,
    columns: Tuple[str, ...],
) -> str:
    """Render a list-based section as Markdown table."""
    if not isinstance(section, dict):
        return "_Section unavailable._"

    items = section.get(key)
    if not isinstance(items, list) or not items:
        error = section.get("error")
        return f"_Section unavailable._{f' Error: {error}' if error else ''}"

    header = "| " + " | ".join(columns) + " |"
    divider = "|" + "|".join(["---"] * len(columns)) + "|"
    rows = [header, divider]

    for item in items:
        values = []
        for col in columns:
            value = item.get(col, "")
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            elif isinstance(value, tuple):
                value = f"{value[0]}–{value[1]}"
            values.append(str(value))
        rows.append("| " + " | ".join(values) + " |")

    return "\n".join(rows)


def _empty_report() -> SpectraReport:
    """Fallback empty report for CSV export edge cases."""
    return SpectraReport(
        molecule_id="",
        molecule_name="",
        input_value="",
        input_format="",
        canonical_smiles="",
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example = "CC(=O)Oc1ccccc1C(=O)O"
    builder = SpectraReportBuilder()
    report = builder.build_report(example, molecule_name="Aspirin")
    print(report.to_markdown())