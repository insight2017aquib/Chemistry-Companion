import pytest
from spectra.proton_nmr import ProtonNMRPredictor

predictor = ProtonNMRPredictor()

@pytest.mark.parametrize("smi, min_downfield", [
    ("c1cc2nccnc2cc1", 8.0),          # parent quinoxaline
    ("c1cc2nccnc2cc1N", 7.8),         # amino substituent may shift slightly
    ("c1cc2nccnc2cc1O", 7.8),         # hydroxy substituent
])
def test_quinoxaline_heterocycle_shifts(smi, min_downfield):
    report = predictor.predict_from_smiles(smi)
    # must detect aromatic environments
    assert any("ar" in e.label.lower() for e in report.environments)
    # at least one environment should be downfield (adjacent to N)
    assert any(e.ppm_range[0] >= min_downfield for e in report.environments)
    # integration sanity check
    total_h = sum(e.integration for e in report.environments)
    # compute expected H count from RDKit
    from rdkit import Chem
    mol = Chem.MolFromSmiles(smi)
    expected_h = sum(int(a.GetTotalNumHs()) for a in mol.GetAtoms() if a.GetAtomicNum() != 1)
    assert total_h == expected_h
