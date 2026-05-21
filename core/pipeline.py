"""
core/pipeline.py
================
Centralized ChemistryPipeline with clean orchestration.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Callable, Protocol

from core.descriptor_utils import compute_descriptors, summarise_descriptors
from core.models import (
    AnalysisResult,
    CarbonNMRPrediction,
    DescriptorRecord,
    FunctionalGroupReport,
    IRPrediction,
    MoleculeRecord,
    ProtonNMRPrediction,
)
from core.molecule_utils import load_molecule
from core.resolver import resolve_molecule_input
from core.visualization_utils import save_2d_image
from reports.export_utils import build_export_row, export_batch

from spectra.carbon_nmr import CarbonNMRPredictor
from spectra.functional_group_detector import FunctionalGroupDetector
from spectra.ir_predictor import IRPredictor
from spectra.proton_nmr import ProtonNMRPredictor

logger = logging.getLogger(__name__)


class PredictorLike(Protocol):
    def predict(self, value: Any) -> Any:
        ...


class DetectorLike(Protocol):
    def detect(self, value: Any) -> Any:
        ...


class ChemistryPipeline:
    """Central orchestration layer for molecular analysis."""

    def __init__(
        self,
        *,
        include_spectra: bool = True,
        fg_detector: DetectorLike | None = None,
        ir_predictor: PredictorLike | None = None,
        proton_predictor: PredictorLike | None = None,
        carbon_predictor: PredictorLike | None = None,
        molecule_loader: Callable[..., MoleculeRecord] = load_molecule,
        descriptor_calculator: Callable[[Any], DescriptorRecord] = compute_descriptors,
        descriptor_summarizer: Callable[[DescriptorRecord], str] = summarise_descriptors,
        image_saver: Callable[..., Any] = save_2d_image,
        export_row_builder: Callable[[MoleculeRecord, DescriptorRecord], dict[str, Any]] = build_export_row,
        batch_exporter: Callable[..., Any] = export_batch,
        pipeline_logger: logging.Logger | None = None,
    ) -> None:
        self.include_spectra = include_spectra
        self.logger = pipeline_logger or logger

        self._molecule_loader = molecule_loader
        self._descriptor_calculator = descriptor_calculator
        self._descriptor_summarizer = descriptor_summarizer
        self._image_saver = image_saver
        self._export_row_builder = export_row_builder
        self._batch_exporter = batch_exporter

        self._fg_detector = fg_detector or FunctionalGroupDetector()
        self._ir_predictor = ir_predictor or IRPredictor()
        self._proton_predictor = proton_predictor or ProtonNMRPredictor()
        self._carbon_predictor = carbon_predictor or CarbonNMRPredictor()

    def analyze(
        self,
        *,
        smiles: str | None = None,
        inchi: str | None = None,
        iupac: str | None = None,
        name: str | None = None,
        save_image: bool = False,
        image_path: str | Path | None = None,
        export: bool = False,
        export_path: str | Path | None = None,
    ) -> AnalysisResult:
        """Run the full centralized analysis pipeline."""
        self.logger.info("Starting chemistry pipeline analysis")

        molecule = self._load_molecule(smiles=smiles, inchi=inchi, iupac=iupac)
        if name:
            molecule.name = name

        descriptors = self._descriptor_calculator(molecule.rdkit_mol)
        descriptor_summary = self._descriptor_summarizer(descriptors)

        public_functional_groups = dict(getattr(descriptors, "functional_groups", {}) or {})
        fg_report = self._detect_functional_groups(molecule.rdkit_mol)

        ir_pred: IRPrediction | None = None
        proton_pred: ProtonNMRPrediction | None = None
        carbon_pred: CarbonNMRPrediction | None = None

        if self.include_spectra:
            ir_pred = self._safe_predict(self._ir_predictor, molecule.rdkit_mol, "IR")
            proton_pred = self._safe_predict(self._proton_predictor, molecule.rdkit_mol, "1H NMR")
            carbon_pred = self._safe_predict(self._carbon_predictor, molecule.rdkit_mol, "13C NMR")

        vis_path = None
        if save_image and image_path is not None:
            vis_path = Path(image_path)
            vis_path.parent.mkdir(parents=True, exist_ok=True)
            self._image_saver(
                molecule.rdkit_mol,
                vis_path,
                title=name or getattr(molecule, "name", None),
            )

        export_row = self._export_row_builder(molecule, descriptors)

        export_path_written = None
        if export and export_path is not None:
            export_path_written = self._export_results(
                molecule=molecule,
                descriptors=descriptors,
                export_path=Path(export_path),
            )

        metadata = {
            "input": {
                "smiles": smiles,
                "inchi": inchi,
                "iupac": iupac,
                "name": name,
            },
            "include_spectra": self.include_spectra,
        }

        # Attach resolution metadata for front-end and API use.
        try:
            input_text = smiles or inchi or iupac or name or ""
            resol = resolve_molecule_input(input_text) if input_text else None
            if resol is not None:
                metadata["resolution"] = {
                    "input": resol.input_text,
                    "detected_type": resol.detected_type,
                    "canonical_smiles": resol.canonical_smiles,
                    "source": resol.source,
                    "success": bool(resol.success),
                    "error": resol.error,
                }
        except Exception:
            self.logger.debug("Failed to attach resolution metadata", exc_info=True)

        return AnalysisResult(
            molecule=molecule,
            descriptors=descriptors,
            descriptor_summary=descriptor_summary,
            functional_groups=public_functional_groups,
            functional_group_report=fg_report,
            ir_prediction=ir_pred,
            proton_nmr_prediction=proton_pred,
            carbon_nmr_prediction=carbon_pred,
            visualization_path=vis_path,
            export_row=export_row,
            export_path=export_path_written,
            metadata=metadata,
        )

    run = analyze

    def _load_molecule(
        self,
        *,
        smiles: str | None,
        inchi: str | None,
        iupac: str | None,
    ) -> MoleculeRecord:
        return self._molecule_loader(
            smiles=smiles,
            inchi=inchi,
            iupac_name=iupac,
        )

    def _detect_functional_groups(self, mol: Any) -> FunctionalGroupReport | None:
        try:
            if self._fg_detector is None:
                return None
            if hasattr(self._fg_detector, "detect"):
                result = self._fg_detector.detect(mol)
            elif callable(self._fg_detector):
                result = self._fg_detector(mol)
            else:
                return None
            return _coerce_fg_report(result)
        except Exception as exc:
            self.logger.warning("Functional-group detection failed: %s", exc)
            return None

    def _safe_predict(self, predictor: PredictorLike, mol: Any, label: str) -> Any | None:
        try:
            if hasattr(predictor, "predict"):
                result = predictor.predict(mol)
            elif callable(predictor):
                result = predictor(mol)
            else:
                self.logger.warning("%s predictor is not callable", label)
                return None
            return result
        except Exception as exc:
            self.logger.warning("%s prediction failed: %s", label, exc)
            return None

    def _export_results(
        self,
        *,
        molecule: MoleculeRecord,
        descriptors: DescriptorRecord,
        export_path: Path,
    ) -> Path:
        export_path = Path(export_path)

        if export_path.suffix:
            fmt = export_path.suffix.lstrip(".").lower()
            output_dir = export_path.parent
            base_name = export_path.stem
            output_dir.mkdir(parents=True, exist_ok=True)

            paths = self._batch_exporter(
                [(molecule, descriptors)],
                output_dir=str(output_dir),
                base_name=base_name,
                formats=[fmt],
            )
            return Path(paths[fmt])

        export_path.mkdir(parents=True, exist_ok=True)
        base_name = _safe_filename(getattr(molecule, "name", None) or "compound")

        paths = self._batch_exporter(
            [(molecule, descriptors)],
            output_dir=str(export_path),
            base_name=base_name,
            formats=["csv"],
        )
        return Path(paths["csv"])


def _coerce_fg_report(value: Any) -> FunctionalGroupReport:
    if value is None:
        return FunctionalGroupReport()

    if isinstance(value, FunctionalGroupReport):
        return value

    if hasattr(value, "to_dict"):
        value = value.to_dict()
    elif hasattr(value, "todict"):
        value = value.todict()

    if isinstance(value, dict):
        counts = dict(value.get("counts", {}))
        names = list(value.get("names", []))
        keys = list(value.get("keys", counts.keys()))
        categories = list(value.get("categories", []))
        summary_text = value.get("summary_text") or value.get("summary") or ""
        smiles = value.get("smiles")
        return FunctionalGroupReport(
            smiles=smiles,
            counts=counts,
            names=names or list(counts.keys()),
            keys=keys or list(counts.keys()),
            categories=categories,
            summary_text=summary_text,
        )

    return FunctionalGroupReport()


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\\\|?*]+', "_", value).strip().strip(".")
    return cleaned or "compound"