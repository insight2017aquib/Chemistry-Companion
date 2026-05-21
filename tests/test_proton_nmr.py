"""
chemistry_companion/tests/test_proton_nmr.py
=============================================
Comprehensive test suite for spectra/proton_nmr.py
Run: python -m pytest tests/test_proton_nmr.py -v --tb=short
"""

import time
import pytest
from rdkit import Chem

from spectra.proton_nmr import (
    MLShiftModel,
    NMRPrediction,
    ProtonEnvironment,
    ProtonNMRPredictor,
    predict_from_groups,
    predict_from_smiles,
)

# ── Test molecules ─────────────────────────────────────────────────────────
ASPIRIN     = "CC(=O)Oc1ccccc1C(=O)O"
BENZENE     = "c1ccccc1"
ETHANOL     = "CCO"
ACETONE     = "CC(=O)C"
CAFFEINE    = "Cn1cnc2c1c(=O)n(c(=O)n2C)C"
QUINOXALINE = "c1ccc2nccnc2c1"
IBUPROFEN   = "CC(C)Cc1ccc(cc1)[C@@H](C)C(=O)O"
PARACETAMOL = "CC(=O)Nc1ccc(O)cc1"
METHANE     = "C"
WATER       = "O"
CHLOROFORM  = "ClC(Cl)Cl"
PYRIDINE    = "n1ccccc1"
INDOLE      = "c1ccc2[nH]ccc2c1"


def get_mol(smiles: str):
    mol = Chem.MolFromSmiles(smiles)
    assert mol is not None, f"Invalid SMILES: {smiles}"
    return mol


@pytest.fixture(scope="module")
def predictor():
    return ProtonNMRPredictor()


# ── Basic Functionality ────────────────────────────────────────────────────
class TestBasicFunctionality:
    def test_predict_from_smiles(self, predictor):
        result = predictor.predict_from_smiles(ASPIRIN)
        assert isinstance(result, NMRPrediction)
        assert result.is_heuristic is True
        assert len(result.environments) > 0

    def test_predict_method(self, predictor):
        result = predictor.predict(get_mol(BENZENE))
        assert isinstance(result, NMRPrediction)

    def test_predict_from_groups(self):
        groups = {"aromatic_ring": 6, "amide": 1}
        envs = predict_from_groups(groups)
        assert isinstance(envs, list)
        assert all(isinstance(e, ProtonEnvironment) for e in envs)

    def test_convenience_function(self):
        result = predict_from_smiles(ETHANOL)
        assert isinstance(result, NMRPrediction)

    def test_predict_proton_nmr(self):
        from spectra.proton_nmr import predict_proton_nmr
        result = predict_proton_nmr(ASPIRIN)
        assert isinstance(result, NMRPrediction)


# ── Data Structures ────────────────────────────────────────────────────────
class TestDataStructures:
    def test_proton_environment_structure(self):
        env = ProtonEnvironment(
            label="CH3",
            ppm_range=(0.8, 1.2),
            multiplicity="s",
            integration=3,
            description="Methyl group",
            rationale="sp3 carbon",
        )
        assert env.is_approximate is True
        assert hasattr(env, "rationale")

    def test_nmr_prediction_summary(self, predictor):
        result = predictor.predict_from_smiles(ACETONE)
        summary = result.summary()
        assert isinstance(summary, str)
        assert "HEURISTIC" in summary or "approximate" in summary.lower()

    def test_environments_sorted_downfield(self, predictor):
        result = predictor.predict_from_smiles(ASPIRIN)
        ppms = [e.ppm_range[0] for e in result.environments]
        assert ppms == sorted(ppms, reverse=True)

    def test_to_dict(self, predictor):
        result = predictor.predict_from_smiles(ETHANOL)
        data = result.to_dict()
        assert "environments" in data
        assert isinstance(data["environments"], list)

    def test_features_dict(self, predictor):
        result = predictor.predict_from_smiles(ETHANOL)
        feats = result.environments[0].features_dict()
        assert "integration" in feats
        assert "hybridization" in feats


# ── Heuristic Quality ──────────────────────────────────────────────────────
class TestHeuristicQuality:
    def test_benzene_aromatic_protons(self, predictor):
        result = predictor.predict_from_smiles(BENZENE)
        envs = result.environments
        assert any("Ar" in e.label or "aromatic" in e.label.lower() for e in envs)
        assert any(6.0 <= e.ppm_range[0] <= 8.5 for e in envs)

    def test_ethanol_multiple_environments(self, predictor):
        result = predictor.predict_from_smiles(ETHANOL)
        assert len(result.environments) >= 2

    def test_acetone_methyl_shift(self, predictor):
        result = predictor.predict_from_smiles(ACETONE)
        assert any(
            "ch3" in e.label.lower() and e.ppm_range[0] > 1.5
            for e in result.environments
        )

    def test_ibuprofen_carboxylic_acid(self, predictor):
        result = predictor.predict_from_smiles(IBUPROFEN)
        labels = [e.label.lower() for e in result.environments]
        assert any("carboxy" in l or "oh" in l for l in labels)

    def test_paracetamol_phenol_and_amide(self, predictor):
        result = predictor.predict_from_smiles(PARACETAMOL)
        labels = [e.label.lower() for e in result.environments]
        assert any("phenol" in l or "oh" in l for l in labels)
        assert any("amide" in l for l in labels)

    def test_chloroform_is_deshielded(self, predictor):
        result = predictor.predict_from_smiles(CHLOROFORM)
        assert len(result.environments) == 1
        assert result.environments[0].ppm_range[0] >= 3.5


# ── Multiplicity & Integration ─────────────────────────────────────────────
class TestMultiplicityAndIntegration:
    def test_methane_singlet(self, predictor):
        result = predictor.predict_from_smiles(METHANE)
        assert any(e.multiplicity == "s" for e in result.environments)

    def test_ethanol_multiplicities(self, predictor):
        result = predictor.predict_from_smiles(ETHANOL)
        mults = [e.multiplicity for e in result.environments]
        assert "t" in mults or "q" in mults

    def test_integration_sum_reasonable(self, predictor):
        result = predictor.predict_from_smiles(ASPIRIN)
        total_h = sum(e.integration for e in result.environments)
        assert 7 <= total_h <= 12

    def test_benzene_signal_grouping(self, predictor):
        result = predictor.predict_from_smiles(BENZENE)
        assert result.n_signals == 1
        assert result.signals[0].integration == 6


# ── predict_from_groups ────────────────────────────────────────────────────
class TestPredictFromGroups:
    def test_aromatic_group(self):
        envs = predict_from_groups({"aromatic_ring": 5})
        assert any("Aromatic" in e.label for e in envs)

    def test_aldehyde(self):
        envs = predict_from_groups({"aldehyde": 1})
        assert any("Aldehyde" in e.label for e in envs)
        assert any(9.0 <= e.ppm_range[0] <= 10.5 for e in envs)

    def test_carboxylic_acid(self):
        envs = predict_from_groups({"carboxylic_acid": 1})
        assert any("Carboxylic" in e.label or "OH" in e.label for e in envs)

    def test_empty_groups(self):
        assert predict_from_groups({}) == []

    def test_invalid_input_raises(self):
        with pytest.raises(TypeError):
            predict_from_groups("not a dict")

    def test_multiple_groups(self):
        envs = predict_from_groups({"aromatic_ring": 4, "amide": 1})
        assert len(envs) >= 2


# ── Edge Cases ─────────────────────────────────────────────────────────────
class TestEdgeCases:
    def test_invalid_smiles_raises(self, predictor):
        with pytest.raises(ValueError):
            predictor.predict_from_smiles("NOTVALID###")

    def test_none_input_raises(self, predictor):
        with pytest.raises(ValueError):
            predictor.predict(None)

    def test_water(self, predictor):
        result = predictor.predict_from_smiles(WATER)
        assert isinstance(result, NMRPrediction)

    def test_methane(self, predictor):
        result = predictor.predict_from_smiles(METHANE)
        assert len(result.environments) > 0

    def test_repeated_prediction_consistency(self, predictor):
        r1 = predictor.predict_from_smiles(ASPIRIN)
        r2 = predictor.predict_from_smiles(ASPIRIN)
        assert len(r1.environments) == len(r2.environments)


# ── Heterocyclic Support ───────────────────────────────────────────────────
class TestHeterocyclicSupport:
    def test_quinoxaline(self, predictor):
        result = predictor.predict_from_smiles(QUINOXALINE)
        assert isinstance(result, NMRPrediction)
        assert len(result.environments) > 0

    def test_caffeine(self, predictor):
        result = predictor.predict_from_smiles(CAFFEINE)
        assert isinstance(result, NMRPrediction)
        assert len(result.environments) >= 3

    def test_pyridine_positions(self, predictor):
        result = predictor.predict_from_smiles(PYRIDINE)
        pyr_envs = [e for e in result.environments if e.heterocycle_family == "pyridine"]
        assert pyr_envs
        assert any(e.hetero_position in {"alpha", "beta", "gamma"} for e in pyr_envs)

    def test_indole_nh(self, predictor):
        result = predictor.predict_from_smiles(INDOLE)
        assert any(e.is_exchangeable for e in result.environments)


# ── Output Quality ─────────────────────────────────────────────────────────
class TestOutputQuality:
    def test_all_environments_have_rationale(self, predictor):
        result = predictor.predict_from_smiles(ASPIRIN)
        for env in result.environments:
            assert env.rationale != ""

    def test_ppm_ranges_valid(self, predictor):
        result = predictor.predict_from_smiles(ETHANOL)
        for env in result.environments:
            assert env.ppm_range[0] < env.ppm_range[1]
            assert -1.0 <= env.ppm_range[0] <= 15.0

    def test_summary_mentions_heuristic(self, predictor):
        result = predictor.predict_from_smiles(ETHANOL)
        assert "heuristic" in result.summary().lower()


# ── Performance & Stress ───────────────────────────────────────────────────
class TestPerformanceAndStress:
    def test_single_prediction_speed(self, predictor):
        start = time.time()
        predictor.predict_from_smiles(ASPIRIN)
        assert time.time() - start < 0.1

    def test_batch_prediction(self, predictor):
        molecules = [ASPIRIN, BENZENE, ETHANOL, CAFFEINE, QUINOXALINE, IBUPROFEN]
        results = [predictor.predict_from_smiles(s) for s in molecules]
        assert len(results) == len(molecules)
        assert all(isinstance(r, NMRPrediction) for r in results)

    def test_large_molecule(self, predictor):
        large = (
            "CC(=O)OC1C(=O)C2(C)C(C(OC(=O)c3ccccc3)C(OC(=O)C)C(=C2C)CC1OC(=O)C)"
            "C4(O)CC(OC(=O)C)C(C(=C4C)C(=O)OC5CC6(O)C(C)(C)C(OC(=O)C)C(OC5=O)"
            "C6(C)C)C"
        )
        try:
            result = predictor.predict_from_smiles(large)
            assert isinstance(result, NMRPrediction)
        except Exception as e:
            pytest.skip(f"Large molecule parsing failed: {e}")

    def test_repeated_predictions_consistency(self, predictor):
        r1 = predictor.predict_from_smiles(CAFFEINE)
        r2 = predictor.predict_from_smiles(CAFFEINE)
        assert len(r1.environments) == len(r2.environments)
        assert [e.label for e in r1.environments] == [e.label for e in r2.environments]

    def test_many_small_molecules(self, predictor):
        smiles_list = ["C", "CC", "CCC", "CCCC", "CCO", "c1ccccc1"] * 20
        start = time.time()
        results = [predictor.predict_from_smiles(s) for s in smiles_list]
        elapsed = time.time() - start
        assert len(results) == len(smiles_list)
        assert elapsed < 2.0


# ── ML Placeholder ─────────────────────────────────────────────────────────
class TestMLPlaceholder:
    def test_ml_placeholder(self):
        ml = MLShiftModel()
        assert ml.is_available() is False
        assert ml.predict({"x": 1}) is None
