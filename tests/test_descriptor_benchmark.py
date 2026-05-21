import csv
from pathlib import Path

from core.descriptor_benchmark import (
    benchmark_from_csv,
    benchmark_molecule,
    benchmark_summary,
    export_benchmark_report,
)


def test_benchmark_molecule_matches_rdkit_reference():
    result = benchmark_molecule("c1ccccc1", name="Benzene")

    assert result.name == "Benzene"
    assert result.smiles == "c1ccccc1"
    assert result.formula_match is True
    assert result.rotatable_bonds_match is True
    assert result.ring_count_match is True
    assert result.logp_agreement is True
    assert result.tpsa_agreement is True
    assert result.mw_error == 0.0


def test_benchmark_from_csv_and_export(tmp_path: Path):
    csv_path = tmp_path / "benchmark_input.csv"
    rows = [
        {"name": "Benzene", "smiles": "c1ccccc1"},
        {"name": "Acetamide", "smiles": "CC(=O)N"},
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["name", "smiles"])
        writer.writeheader()
        writer.writerows(rows)

    comparisons = benchmark_from_csv(csv_path)
    assert len(comparisons) == 2
    assert all(c.formula_match for c in comparisons)

    summary = benchmark_summary(comparisons)
    assert summary.n_molecules == 2
    assert summary.formula_accuracy == 100.0
    assert summary.rotatable_bonds_accuracy == 100.0
    assert summary.ring_count_accuracy == 100.0
    assert summary.full_agreement == 100.0

    outputs = export_benchmark_report(comparisons, output_dir=tmp_path, base_name="benchmark_test")
    assert Path(outputs["csv"]).exists()
    assert Path(outputs["xlsx"]).exists()
    assert all(Path(outputs[key]).exists() for key in outputs if key.startswith("figure_"))
