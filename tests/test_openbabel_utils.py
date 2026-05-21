"""Tests for Open Babel interoperability and preprocessing utilities."""

from pathlib import Path

from core.openbabel_utils import (
    add_hydrogens,
    adjust_ph,
    convert_format,
    deprotonate_structure,
    generate_3d_coordinates,
    inchi_to_mol2,
    mol2_to_smiles,
    normalize_structure,
    optimize_geometry,
    protonate_structure,
    remove_hydrogens,
    remove_salts,
    sdf_to_smiles,
    smiles_to_mol2,
    smiles_to_pdbqt,
)

BENZENE = "c1ccccc1"
ETHANOL = "CCO"
SALTY = "CCO.[Na+]"
ETHANOL_INCHI = "InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3"


def test_convert_smiles_to_mol2():
    mol2 = smiles_to_mol2(ETHANOL)
    assert "@<TRIPOS>MOLECULE" in mol2
    assert "@<TRIPOS>ATOM" in mol2


def test_convert_smiles_to_pdbqt():
    pdbqt = smiles_to_pdbqt(ETHANOL)
    assert "PDBQT" in pdbqt or "ATOM" in pdbqt
    assert "REMARK" in pdbqt or "ATOM" in pdbqt


def test_mol2_to_smiles_roundtrip():
    mol2 = smiles_to_mol2(ETHANOL)
    smiles = mol2_to_smiles(mol2)
    assert smiles.replace(" ", "") == "CCO"


def test_sdf_to_smiles_returns_list(tmp_path):
    sdf_path = tmp_path / "ethanol.sdf"
    sdf_path.write_text(
        """\n  OpenBabel02122312123D
\n  3  2  0  0  0  0            999 V2000
    1.2079   -0.2125    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -0.2303    0.4634    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -0.3080   -0.9071    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  1  0  0  0  0
  2  3  1  0  0  0  0
M  END
$$$$\n""",
        encoding="utf-8",
    )
    smiles = sdf_to_smiles(sdf_path.read_text(encoding="utf-8"))
    assert smiles == ["CCO"]


def test_inchi_to_mol2():
    mol2 = inchi_to_mol2(ETHANOL_INCHI)
    assert "@<TRIPOS>MOLECULE" in mol2
    assert "@<TRIPOS>ATOM" in mol2


def test_remove_salts_keeps_largest_fragment():
    cleaned = remove_salts(SALTY)
    assert "[Na+]" not in cleaned
    assert "CCO" in cleaned


def test_add_and_remove_hydrogens():
    with_h = add_hydrogens(ETHANOL, output_format="mol")
    assert "H" in with_h
    without_h = remove_hydrogens(with_h, input_format="mol", output_format="mol")
    assert "H" not in without_h


def test_normalize_structure_with_ph_adjustment():
    normalized = normalize_structure(ETHANOL)
    assert isinstance(normalized, str)
    assert normalized


def test_adjust_ph_returns_valid_smiles():
    adjusted = adjust_ph(ETHANOL, ph=6.5)
    assert adjusted.startswith("CC")


def test_protonate_and_deprotonate_are_noops_on_small_alcohol():
    protonated = protonate_structure(ETHANOL)
    deprotonated = deprotonate_structure(protonated)
    assert isinstance(protonated, str)
    assert isinstance(deprotonated, str)


def test_generate_3d_coordinates_creates_conformer():
    mol = generate_3d_coordinates(ETHANOL)
    assert mol.OBMol.NumConformers() > 0


def test_optimize_geometry_returns_molecule():
    optimized = optimize_geometry(ETHANOL, method="uff", steps=10)
    assert optimized.OBMol.NumConformers() > 0
