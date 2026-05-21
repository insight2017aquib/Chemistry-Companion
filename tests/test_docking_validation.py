"""Tests for docking preparation validation workflow."""

from pathlib import Path

from core.docking_validation import (
    DockingValidationReport,
    validate_docking_workflow,
    export_validation_report,
)


def test_validate_docking_workflow_success_and_failure(tmp_path):
    inputs = ["CCO", "C1CCCCC1", "not-a-smiles", ""]
    report = validate_docking_workflow(inputs, output_format="pdbqt", optimization_steps=10)

    assert isinstance(report, DockingValidationReport)
    assert report.total() == 4
    assert report.successes() == 2
    assert report.failures() == 2
    assert report.success_rate() == 50.0
    assert report.average_generation_time() is not None
    assert report.average_optimization_time() is not None
    assert report.average_export_time() is not None
    assert report.failure_breakdown()["validation"] == 2


def test_export_validation_report_creates_files(tmp_path):
    inputs = ["CCO", "CCN"]
    report = validate_docking_workflow(inputs, output_format="pdbqt", optimization_steps=10)
    xlsx_path = tmp_path / "docking_validation.xlsx"
    md_path = tmp_path / "docking_validation.md"

    xlsx_target, md_target = export_validation_report(report, xlsx_path, markdown_path=md_path)

    assert xlsx_target.exists()
    assert md_target is not None and md_target.exists()

    text = md_target.read_text(encoding="utf-8")
    assert "Docking Preparation Validation Report" in text
    assert "success_rate" in text.lower() or "success rate" in text.lower()


def test_coordinate_generation_consistency(tmp_path):
    report = validate_docking_workflow(["CCO"], output_format="pdbqt", optimization_steps=10)
    assert report.total() == 1
    record = report.records[0]
    assert record.success
    assert record.initial_atoms == 3
    assert record.initial_heavy_atoms == 3
    assert record.conformer_count is not None and record.conformer_count > 0
    assert record.output_size is not None and record.output_size > 0
    assert record.pdbqt_compatible is True
