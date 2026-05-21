"""Tests for the docking preparation workflow."""

import pytest

from core.docking_preparation import prepare_docking_structure


def test_prepare_docking_structure_returns_pdbqt():
    pdbqt = prepare_docking_structure("CCO")
    assert isinstance(pdbqt, str)
    assert pdbqt.strip()
    assert "ATOM" in pdbqt or "HETATM" in pdbqt
    assert "REMARK" in pdbqt or "PDBQT" in pdbqt


def test_prepare_docking_structure_invalid_smiles_raises():
    with pytest.raises(ValueError, match="Invalid SMILES"):
        prepare_docking_structure("not-a-smiles")


def test_prepare_docking_structure_supports_other_output_formats():
    mol_block = prepare_docking_structure("CCO", output_format="mol")
    assert mol_block.startswith("OpenBabel") or mol_block.startswith("\n")
    assert "M  END" in mol_block
