"""
chemistry_companion/tests/test_phase1.py
Run: cd chemistry_companion && pytest tests/test_phase1.py -v
"""
import os, sys, pytest, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rdkit import Chem
from core.molecule_utils import mol_from_smiles, build_record, load_molecule, count_atoms
from core.descriptor_utils import compute_descriptors
from core.conversion_utils import smiles_to_inchi, smiles_to_inchikey, inchi_to_smiles, embed_3d, mol_to_xyz
from reports.export_utils import record_to_dict, build_dataframe, export_csv

BENZENE   = "c1ccccc1"
ASPIRIN   = "CC(=O)Oc1ccccc1C(=O)O"
CAFFEINE  = "Cn1cnc2c1c(=O)n(c(=O)n2C)C"
IBUPROFEN = "CC(C)Cc1ccc(cc1)[C@@H](C)C(=O)O"


class TestMoleculeUtils:
    def test_valid_smiles(self):
        assert mol_from_smiles(BENZENE).GetNumAtoms() == 6

    def test_invalid_smiles_raises(self):
        with pytest.raises(ValueError, match="RDKit could not parse"):
            mol_from_smiles("INVALID!!!")

    def test_benzene_formula(self):
        rec = build_record(mol_from_smiles(BENZENE), name="Benzene")
        assert rec.formula == "C6H6"
        assert rec.num_rings == 1
        assert rec.is_aromatic is True

    def test_heavy_vs_total_atoms(self):
        rec = build_record(mol_from_smiles(ASPIRIN))
        assert rec.num_atoms > rec.num_heavy_atoms
        assert rec.num_heavy_atoms == 13

    def test_inchikey_length(self):
        assert len(load_molecule(smiles=ASPIRIN).inchikey) == 27

    def test_no_input_raises(self):
        with pytest.raises(ValueError, match="No input provided"):
            load_molecule()

    def test_multi_input_raises(self):
        with pytest.raises(ValueError, match="Multiple inputs"):
            load_molecule(smiles=BENZENE, inchi="InChI=1S/C6H6")

    def test_whitespace_stripped(self):
        assert load_molecule(smiles=f"  {ASPIRIN}  ").formula == "C9H8O4"

    def test_caffeine_formula(self):
        assert load_molecule(smiles=CAFFEINE).formula == "C8H10N4O2"


class TestDescriptorUtils:
    def test_aspirin_lipinski(self):
        desc = compute_descriptors(Chem.MolFromSmiles(ASPIRIN))
        assert 0.5 < desc.logp < 2.5
        assert desc.ro5_pass is True
        assert desc.ro5_violations == 0

    def test_ro5_details_keys(self):
        desc = compute_descriptors(Chem.MolFromSmiles(ASPIRIN))
        for rule, d in desc.ro5_details.items():
            assert all(k in d for k in ("value","threshold","pass"))

    def test_aspirin_functional_groups(self):
        desc = compute_descriptors(Chem.MolFromSmiles(ASPIRIN))
        assert "Carboxylic acid" in desc.functional_groups or "Ester" in desc.functional_groups

    def test_all_fields_present(self):
        desc = compute_descriptors(Chem.MolFromSmiles(BENZENE))
        for attr in ("logp","tpsa","hbd","hba","rotatable_bonds",
                     "ro5_pass","ro5_violations","ro5_details","bertz_ct","functional_groups"):
            assert hasattr(desc, attr)


class TestConversionUtils:
    def test_inchi_prefix(self):
        assert smiles_to_inchi(BENZENE).startswith("InChI=")

    def test_inchikey_27_chars(self):
        assert len(smiles_to_inchikey(BENZENE)) == 27

    def test_round_trip_inchi(self):
        from rdkit.Chem.rdMolDescriptors import CalcMolFormula
        back = inchi_to_smiles(smiles_to_inchi(ASPIRIN))
        assert CalcMolFormula(Chem.MolFromSmiles(ASPIRIN)) == CalcMolFormula(Chem.MolFromSmiles(back))

    def test_embed_3d_conformer(self):
        assert embed_3d(Chem.MolFromSmiles(ASPIRIN), optimize=False).GetNumConformers() == 1

    def test_xyz_line_count(self):
        mol3d = embed_3d(Chem.MolFromSmiles(BENZENE), optimize=False)
        lines = mol_to_xyz(mol3d).strip().splitlines()
        assert len(lines) == int(lines[0]) + 2


class TestExportUtils:
    def _pair(self, smi, name):
        mol = Chem.MolFromSmiles(smi)
        mr  = build_record(mol, name=name)
        dr  = compute_descriptors(mol, mw=mr.mol_weight)
        return mr, dr

    def test_required_keys(self):
        mr, dr = self._pair(BENZENE, "Benzene")
        row = record_to_dict(mr, dr)
        for k in ("Name","SMILES","Formula","MW (Da)","LogP","TPSA (A2)","Ro5 Pass"):
            assert k in row

    def test_ro5_detail_columns(self):
        mr, dr = self._pair(ASPIRIN, "Aspirin")
        row = record_to_dict(mr, dr)
        assert len([k for k in row if k.startswith("Ro5: ")]) == 4

    def test_total_atoms_column(self):
        mr, dr = self._pair(ASPIRIN, "Aspirin")
        row = record_to_dict(mr, dr)
        assert row["Total Atoms"] > row["Heavy Atoms"]

    def test_csv_roundtrip(self, tmp_path):
        mr, dr = self._pair(ASPIRIN, "Aspirin")
        df     = build_dataframe([record_to_dict(mr, dr)])
        path   = str(tmp_path / "test.csv")
        export_csv(df, path)
        assert pd.read_csv(path).iloc[0]["Formula"] == "C9H8O4"