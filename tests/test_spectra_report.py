"""
chemistry_companion/tests/test_spectra_report.py
================================================

Pytest tests for reports/spectra_report.py
"""

from __future__ import annotations

import json

import pytest
from rdkit import Chem

from reports.spectra_report import (
    BatchSpectraReport,
    FunctionalGroupAnalysis,
    SpectraReport,
    SpectraReportBuilder,
    build_batch_spectra_reports,
    build_spectra_report,
)


class FakeIRPrediction:
    def __init__(self) -> None:
        self.fg_keys = ["ester", "aromatic_ring"]
        self.fg_names = ["Ester", "Aromatic ring"]
        self.bands = [
            {
                "label": "C=O stretch",
                "low_cm": 1735,
                "high_cm": 1750,
                "intensity": "strong",
            },
            {
                "label": "Ar C=C stretch",
                "low_cm": 1450,
                "high_cm": 1600,
                "intensity": "medium",
            },
        ]
        self.peaks = [
            {
                "functional_group": "Ester",
                "wavenumber_range": [1735, 1750],
                "intensity": "strong",
                "description": "C=O stretch",
            }
        ]
        self.n_bands = len(self.bands)
        self.is_heuristic = True

    def to_dict(self):
        return {
            "fg_keys": self.fg_keys,
            "fg_names": self.fg_names,
            "bands": self.bands,
            "peaks": self.peaks,
            "n_bands": self.n_bands,
            "is_heuristic": self.is_heuristic,
        }


class FakeProtonPrediction:
    def __init__(self) -> None:
        self.signals = [
            {
                "label": "Aromatic CH",
                "ppm_range": [7.1, 8.0],
                "multiplicity": "m",
                "integration": 4,
            },
            {
                "label": "CH3",
                "ppm_range": [2.1, 2.4],
                "multiplicity": "s",
                "integration": 3,
            },
        ]
        self.environments = list(self.signals)
        self.n_signals = len(self.signals)
        self.total_H = 7
        self.is_heuristic = True

    def to_dict(self):
        return {
            "signals": self.signals,
            "environments": self.environments,
            "n_signals": self.n_signals,
            "total_H": self.total_H,
            "is_heuristic": self.is_heuristic,
        }


class FakeCarbonPrediction:
    def __init__(self) -> None:
        self.environments = [
            {
                "label": "ester C=O carbon",
                "ppm_range": [165.0, 175.0],
                "carbon_count": 1,
                "annotation": "Ester carbonyl carbon",
            },
            {
                "label": "Ar CH carbon",
                "ppm_range": [120.0, 132.0],
                "carbon_count": 6,
                "annotation": "Benzenoid aromatic carbon",
            },
        ]
        self.n_signals = len(self.environments)
        self.total_carbons = 8
        self.is_heuristic = True

    def to_dict(self):
        return {
            "environments": self.environments,
            "n_signals": self.n_signals,
            "total_carbons": self.total_carbons,
            "is_heuristic": self.is_heuristic,
        }


class FakeIRPredictor:
    def predict(self, mol):
        return FakeIRPrediction()


class FakeProtonPredictor:
    def predict(self, mol):
        return FakeProtonPrediction()


class FakeCarbonPredictor:
    def predict(self, mol):
        return FakeCarbonPrediction()


def fake_fg_detector(mol):
    return {
        "keys": ["ester", "aromatic_ring"],
        "names": ["Ester", "Aromatic ring"],
        "counts": {"Ester": 1, "Aromatic ring": 1},
    }


@pytest.fixture
def builder():
    return SpectraReportBuilder(
        ir_predictor=FakeIRPredictor(),
        proton_predictor=FakeProtonPredictor(),
        carbon_predictor=FakeCarbonPredictor(),
        fg_detector=fake_fg_detector,
    )


def test_build_single_report_from_smiles(builder):
    report = builder.build_report("CC(=O)Oc1ccccc1C(=O)O", molecule_name="Aspirin")
    assert isinstance(report, SpectraReport)
    assert report.molecule_name == "Aspirin"
    assert report.input_format == "smiles"
    assert report.canonical_smiles != ""
    assert report.ir["n_bands"] == 2
    assert report.proton_nmr["n_signals"] == 2
    assert report.carbon_nmr["n_signals"] == 2
    assert "Ester" in report.functional_groups.names


def test_build_single_report_from_mol(builder):
    mol = Chem.MolFromSmiles("CCO")
    assert mol is not None
    report = builder.build_report(mol, molecule_name="Ethanol")
    assert isinstance(report, SpectraReport)
    assert report.input_format == "mol"
    assert report.canonical_smiles != ""


def test_invalid_smiles_raises(builder):
    with pytest.raises(ValueError):
        builder.build_report("INVALID###")


def test_markdown_render(builder):
    report = builder.build_report("CCO", molecule_name="Ethanol")
    text = report.to_markdown()
    assert "# Spectral Report:" in text
    assert "## IR" in text
    assert "## 1H NMR" in text
    assert "## 13C NMR" in text
    assert "Functional Groups" in text


def test_json_export(builder, tmp_path):
    report = builder.build_report("CCO", molecule_name="Ethanol")
    out = tmp_path / "spectra.json"
    builder.export_json(report, out)
    assert out.exists()

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["molecule_name"] == "Ethanol"
    assert data["ir"]["n_bands"] == 2


def test_csv_export_single(builder, tmp_path):
    report = builder.build_report("CCO", molecule_name="Ethanol")
    out = tmp_path / "spectra.csv"
    builder.export_csv(report, out)
    text = out.read_text(encoding="utf-8")
    assert "molecule_name" in text
    assert "Ethanol" in text
    assert "ir_band_count" in text


def test_markdown_export(builder, tmp_path):
    report = builder.build_report("CCO", molecule_name="Ethanol")
    out = tmp_path / "spectra.md"
    builder.export_markdown(report, out)
    text = out.read_text(encoding="utf-8")
    assert "Spectral Report" in text
    assert "Ethanol" in text


def test_build_batch_reports(builder):
    batch = builder.build_batch(
        [
            {"input": "CCO", "name": "Ethanol", "id": "mol-1"},
            {"input": "CC(=O)Oc1ccccc1C(=O)O", "name": "Aspirin", "id": "mol-2"},
        ]
    )
    assert isinstance(batch, BatchSpectraReport)
    assert batch.n_reports == 2
    assert batch.n_failed == 0
    assert batch.reports[0].molecule_id == "mol-1"


def test_batch_with_failure(builder):
    batch = builder.build_batch(["CCO", "INVALID###"])
    assert batch.n_reports == 1
    assert batch.n_failed == 1
    assert "Could not parse SMILES" in batch.failed_items[0]["error"]


def test_batch_json_csv_markdown_exports(builder, tmp_path):
    batch = builder.build_batch(
        [
            {"input": "CCO", "name": "Ethanol"},
            {"input": "CCN", "name": "Ethylamine"},
        ]
    )

    json_path = tmp_path / "batch.json"
    csv_path = tmp_path / "batch.csv"
    md_path = tmp_path / "batch.md"

    builder.export_json(batch, json_path)
    builder.export_csv(batch, csv_path)
    builder.export_markdown(batch, md_path)

    assert json_path.exists()
    assert csv_path.exists()
    assert md_path.exists()

    assert "Successful reports" in md_path.read_text(encoding="utf-8")
    assert "molecule_id" in csv_path.read_text(encoding="utf-8")


def test_functional_group_analysis_to_dict():
    fg = FunctionalGroupAnalysis(
        keys=["ester"],
        names=["Ester"],
        counts={"Ester": 1},
        source="unit-test",
    )
    data = fg.to_dict()
    assert data["source"] == "unit-test"
    assert data["counts"]["Ester"] == 1


def test_convenience_wrappers():
    report = build_spectra_report(
        "CCO",
        molecule_name="Ethanol",
        ir_predictor=FakeIRPredictor(),
        proton_predictor=FakeProtonPredictor(),
        carbon_predictor=FakeCarbonPredictor(),
        fg_detector=fake_fg_detector,
    )
    assert isinstance(report, SpectraReport)

    batch = build_batch_spectra_reports(
        ["CCO", "CCN"],
        ir_predictor=FakeIRPredictor(),
        proton_predictor=FakeProtonPredictor(),
        carbon_predictor=FakeCarbonPredictor(),
        fg_detector=fake_fg_detector,
    )
    assert isinstance(batch, BatchSpectraReport)
    assert batch.n_reports == 2


def test_missing_predictors_are_handled():
    builder = SpectraReportBuilder(
        ir_predictor=None,
        proton_predictor=None,
        carbon_predictor=None,
        fg_detector=None,
    )

    report = builder.build_report("CCO")
    assert isinstance(report, SpectraReport)
    assert isinstance(report.warnings, list)
    assert report.is_heuristic is True