"""Tests for core.spectra_validation validation workflows."""

from __future__ import annotations

from pathlib import Path

from core.spectra_validation import (
    SpectraDomainMetrics,
    SpectraValidationRecord,
    SpectraValidationReport,
    build_markdown_report,
    export_validation_report,
    validate_spectra_workflow,
)


class FakeIRPrediction:
    def __init__(self) -> None:
        self.bands = [
            {"low_cm": 1700, "high_cm": 1720},
            {"low_cm": 3010, "high_cm": 3040},
        ]


class FakeProtonPrediction:
    def __init__(self) -> None:
        self.signals = [
            {"ppm_range": [1.0, 1.5]},
            {"ppm_range": [7.0, 7.5]},
        ]


class FakeCarbonPrediction:
    def __init__(self) -> None:
        self.environments = [
            {"ppm_range": [10.0, 10.5]},
            {"ppm_range": [123.0, 127.0]},
        ]


class FakePredictorModule:
    def __init__(self, ir_pred=None, proton_pred=None, carbon_pred=None) -> None:
        self.ir_pred = ir_pred or FakeIRPrediction()
        self.proton_pred = proton_pred or FakeProtonPrediction()
        self.carbon_pred = carbon_pred or FakeCarbonPrediction()

    def predict_ir(self, _mol):
        return self.ir_pred

    def predict_proton_nmr(self, _mol):
        return self.proton_pred

    def predict_carbon_nmr(self, _mol):
        return self.carbon_pred


def test_validate_spectra_workflow_computes_metrics(monkeypatch):
    fake = FakePredictorModule()
    monkeypatch.setattr("core.spectra_validation.predict_ir", lambda mol: fake.predict_ir(mol))
    monkeypatch.setattr("core.spectra_validation.predict_proton_nmr", lambda mol: fake.predict_proton_nmr(mol))
    monkeypatch.setattr("core.spectra_validation.predict_carbon_nmr", lambda mol: fake.predict_carbon_nmr(mol))

    inputs = [
        {
            "smiles": "CCO",
            "experimental_ir": [1710, 3025],
            "experimental_proton": [1.25, 7.25],
            "experimental_carbon": [10.25, 125.0],
        }
    ]
    report = validate_spectra_workflow(inputs, ir_tolerance=20.0, proton_tolerance=0.5, carbon_tolerance=5.0)

    assert isinstance(report, SpectraValidationReport)
    assert report.total() == 1
    record = report.records[0]
    assert record.success is True
    assert record.ir_metrics is not None
    assert record.proton_metrics is not None
    assert record.carbon_metrics is not None
    assert record.ir_metrics.matched_count == 2
    assert record.proton_metrics.matched_count == 2
    assert record.carbon_metrics.matched_count == 2
    assert record.ir_metrics.mae == 0.0
    assert record.proton_metrics.mae == 0.0
    assert record.carbon_metrics.mae == 0.0


def test_export_validation_report_creates_files(tmp_path):
    metrics = SpectraDomainMetrics(domain="ir", predicted_count=1, experimental_count=1, matched_count=1, mae=0.0, rmse=0.0, coverage_predicted=1.0, coverage_experimental=1.0, missing_experimental=0, extra_predicted=0, tolerance=50.0)
    record = SpectraValidationRecord(
        input_smiles="CCO",
        molecule_name="Ethanol",
        canonical_smiles="CCO",
        ir_metrics=metrics,
        proton_metrics=metrics,
        carbon_metrics=metrics,
        success=True,
    )
    report = SpectraValidationReport(records=[record])

    xlsx_path = tmp_path / "spectra_validation.xlsx"
    md_path = tmp_path / "spectra_validation.md"
    plot_dir = tmp_path / "plots"

    xlsx_target, markdown_target, plot_paths = export_validation_report(
        report,
        xlsx_path=xlsx_path,
        markdown_path=md_path,
        plot_dir=plot_dir,
    )

    assert xlsx_target.exists()
    assert markdown_target is not None and markdown_target.exists()
    assert plot_dir.exists()
    assert len(plot_paths) == 2
    for path in plot_paths:
        assert path.exists()


def test_build_markdown_report_includes_domain_headings():
    metrics = SpectraDomainMetrics(domain="ir", predicted_count=0, experimental_count=0, matched_count=0, tolerance=50.0)
    report = SpectraValidationReport(records=[SpectraValidationRecord(input_smiles="CCO", canonical_smiles="CCO", ir_metrics=metrics, proton_metrics=metrics, carbon_metrics=metrics, success=True)])
    text = build_markdown_report(report)
    assert "# Spectra Validation Report" in text
    assert "### IR" in text
    assert "### 1H NMR" in text
    assert "### 13C NMR" in text
    assert "Record Details" in text
