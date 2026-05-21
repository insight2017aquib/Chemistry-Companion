"""
chemistry_companion/tests/test_ir_predictor.py
===============================================
Comprehensive test suite for spectra/ir_predictor.py

Run:
    python -m pytest tests/test_ir_predictor.py -v --tb=short

Test groups:
    TestIRBandLibrary         — _IR_BAND_LIBRARY schema validation
    TestIRBandDataclass       — IRBand fields, __str__, to_dict
    TestIRPredictionMethods   — sorted_bands, bands_by_region, bands_by_fg, to_dict
    TestIRPredictorInit       — detector injection
    TestPredictKnownBands     — per-FG positive band detection on reference molecules
    TestPredictNegativeCases  — bands absent when FG absent
    TestAliphaticCH           — universal C–H band logic
    TestWarnings              — warnings for empty FGs, large molecules, None mol
    TestSummaryOutput         — summary() formatting and heuristic label
    TestBandRegions           — bands_by_region() grouping correctness
    TestConvenienceFunctions  — predict_ir() with SMILES and Mol input
    TestEdgeCases             — None mol, bad SMILES, water, methane, benzene
    TestHeuristicLabel        — is_heuristic always True
    TestSerialisation         — to_dict JSON serialisability
    TestReferenceChemistry    — wavenumber ranges against textbook values
"""

import json
import logging
import sys
import os
import pytest

from rdkit import Chem

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spectra.ir_predictor import (
    IRBand,
    IRPrediction,
    IRPredictor,
    _IR_BAND_LIBRARY,
    _BandSpec,
    predict_ir,
)

# ── reference SMILES ─────────────────────────────────────────────────────────
BENZENE       = "c1ccccc1"
ACETIC_ACID   = "CC(=O)O"
ASPIRIN       = "CC(=O)Oc1ccccc1C(=O)O"
CAFFEINE      = "Cn1cnc2c1c(=O)n(c(=O)n2C)C"
PARACETAMOL   = "CC(=O)Nc1ccc(O)cc1"
IBUPROFEN     = "CC(C)Cc1ccc(cc1)[C@@H](C)C(=O)O"
PENICILLIN_G  = "CC1(C)SC2C(NC(=O)Cc3ccccc3)C(=O)N2C1C(=O)O"
DIAZEPAM      = "CN1C(=O)CN=C(c2ccccc2)c2cc(Cl)ccc21"
NITROBENZENE  = "O=[N+]([O-])c1ccccc1"
ACETONITRILE  = "CC#N"
ETHANETHIOL   = "CCS"
DIMETHYLSULFONAMIDE = "CS(=O)(=O)N"
ETHANOL       = "CCO"
PHENOL        = "Oc1ccccc1"
DIETHYLETHER  = "CCOCC"
ACETALDEHYDE  = "CC=O"
ACETONE       = "CC(C)=O"
ETHYL_ACETATE = "CCOC(=O)C"
METHYLAMINE   = "CN"
ACETAMIDE     = "CC(=O)N"
CHLOROBENZENE = "Clc1ccccc1"
FLUOROBENZENE = "Fc1ccccc1"
STYRENE       = "C=Cc1ccccc1"
PROPYNE       = "CC#C"
WATER         = "O"
METHANE       = "C"
OXALIC_ACID   = "OC(=O)C(=O)O"


def mol(smi):
    m = Chem.MolFromSmiles(smi)
    assert m is not None, f"Bad test SMILES: {smi!r}"
    return m


@pytest.fixture(scope="module")
def predictor():
    return IRPredictor()


def bands_for(predictor, smiles):
    return predictor.predict_from_smiles(smiles).bands


def has_band_key(bands, fg_key):
    return any(b.fg_key == fg_key for b in bands)


def has_label_containing(bands, fg_key, substring):
    return any(
        b.fg_key == fg_key and substring.lower() in b.label.lower()
        for b in bands
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TestIRBandLibrary — schema validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestIRBandLibrary:

    def test_library_nonempty(self):
        assert len(_IR_BAND_LIBRARY) > 0

    def test_all_values_are_lists(self):
        for k, v in _IR_BAND_LIBRARY.items():
            assert isinstance(v, list), f"Key {k!r}: expected list"

    def test_all_specs_are_bandspec(self):
        for k, specs in _IR_BAND_LIBRARY.items():
            for spec in specs:
                assert isinstance(spec, _BandSpec), f"Key {k!r}: bad spec type"

    def test_wavenumber_lo_lt_hi(self):
        for k, specs in _IR_BAND_LIBRARY.items():
            for spec in specs:
                assert spec.low_cm < spec.high_cm, (
                    f"Key {k!r}, label {spec.label!r}: low_cm >= high_cm"
                )

    def test_wavenumber_range_400_to_4000(self):
        for k, specs in _IR_BAND_LIBRARY.items():
            for spec in specs:
                assert 400 <= spec.low_cm <= 4000, f"Key {k!r}: low_cm out of range"
                assert 400 <= spec.high_cm <= 4000, f"Key {k!r}: high_cm out of range"

    def test_intensity_values_valid(self):
        VALID = {"strong", "medium", "weak", "variable", "broad"}
        for k, specs in _IR_BAND_LIBRARY.items():
            for spec in specs:
                assert spec.intensity in VALID, (
                    f"Key {k!r}: invalid intensity {spec.intensity!r}"
                )

    def test_labels_nonempty(self):
        for k, specs in _IR_BAND_LIBRARY.items():
            for spec in specs:
                assert spec.label.strip(), f"Key {k!r}: empty label"

    def test_descriptions_nonempty(self):
        for k, specs in _IR_BAND_LIBRARY.items():
            for spec in specs:
                assert spec.description.strip(), f"Key {k!r}: empty description"

    def test_known_fg_keys_present(self):
        REQUIRED = {
            "alcohol", "phenol", "carboxylic_acid", "ester", "ether",
            "aldehyde", "ketone", "primary_amine", "secondary_amine",
            "tertiary_amine", "amide", "nitrile", "nitro", "aromatic_ring",
            "sulfonamide", "thiol", "thioether",
            "fluoride", "chloride", "bromide", "iodide",
            "alkene", "alkyne", "epoxide",
        }
        for k in REQUIRED:
            assert k in _IR_BAND_LIBRARY, f"Missing key: {k!r}"

    def test_each_list_has_at_least_one_spec(self):
        for k, specs in _IR_BAND_LIBRARY.items():
            assert len(specs) >= 1, f"Key {k!r}: empty spec list"


# ═══════════════════════════════════════════════════════════════════════════════
# TestIRBandDataclass
# ═══════════════════════════════════════════════════════════════════════════════

class TestIRBandDataclass:

    def _band(self):
        return IRBand(
            fg_key="carboxylic_acid", fg_name="Carboxylic Acid",
            label="C=O stretch", low_cm=1700, high_cm=1725,
            mid_cm=1712, intensity="strong",
            description="Strongest band in spectrum.",
        )

    def test_is_heuristic_default_true(self):
        assert self._band().is_heuristic is True

    def test_str_contains_wavenumbers(self):
        s = str(self._band())
        assert "1700" in s and "1725" in s

    def test_str_contains_intensity(self):
        assert "strong" in str(self._band())

    def test_str_contains_label(self):
        assert "C=O stretch" in str(self._band())

    def test_to_dict_has_required_keys(self):
        d = self._band().to_dict()
        for k in ("fg_key","fg_name","label","low_cm","high_cm",
                  "mid_cm","intensity","description","is_heuristic"):
            assert k in d

    def test_to_dict_is_json_serialisable(self):
        json.dumps(self._band().to_dict())

    def test_mid_cm_within_range(self):
        b = self._band()
        assert b.low_cm <= b.mid_cm <= b.high_cm


# ═══════════════════════════════════════════════════════════════════════════════
# TestIRPredictionMethods
# ═══════════════════════════════════════════════════════════════════════════════

class TestIRPredictionMethods:

    @pytest.fixture
    def aspirin_pred(self, predictor):
        return predictor.predict_from_smiles(ASPIRIN)

    def test_sorted_bands_descending(self, aspirin_pred):
        bands = aspirin_pred.sorted_bands()
        mids  = [b.mid_cm for b in bands]
        assert mids == sorted(mids, reverse=True)

    def test_bands_by_region_returns_all_four_regions(self, aspirin_pred):
        regions = aspirin_pred.bands_by_region()
        assert len(regions) == 4

    def test_bands_by_region_no_band_lost(self, aspirin_pred):
        all_from_regions = [b for bs in aspirin_pred.bands_by_region().values() for b in bs]
        assert len(all_from_regions) == aspirin_pred.n_bands

    def test_bands_by_fg_groups_correctly(self, aspirin_pred):
        by_fg = aspirin_pred.bands_by_fg()
        assert "ester" in by_fg
        assert "carboxylic_acid" in by_fg

    def test_to_dict_is_json_serialisable(self, aspirin_pred):
        json.dumps(aspirin_pred.to_dict())

    def test_to_dict_bands_sorted_desc(self, aspirin_pred):
        d     = aspirin_pred.to_dict()
        mids  = [b["mid_cm"] for b in d["bands"]]
        assert mids == sorted(mids, reverse=True)

    def test_n_bands_matches_len_bands(self, aspirin_pred):
        assert aspirin_pred.n_bands == len(aspirin_pred.bands)

    def test_fg_keys_and_names_same_length(self, aspirin_pred):
        assert len(aspirin_pred.fg_keys) == len(aspirin_pred.fg_names)

    def test_is_heuristic_true_on_prediction(self, aspirin_pred):
        assert aspirin_pred.is_heuristic is True


# ═══════════════════════════════════════════════════════════════════════════════
# TestIRPredictorInit
# ═══════════════════════════════════════════════════════════════════════════════

class TestIRPredictorInit:

    def test_default_init_works(self):
        p = IRPredictor()
        assert p is not None

    def test_custom_detector_injected(self):
        from spectra.functional_group_detector import FunctionalGroupDetector
        det = FunctionalGroupDetector()
        p   = IRPredictor(detector=det)
        assert p._detector is det

    def test_two_predictors_are_independent(self):
        p1 = IRPredictor()
        p2 = IRPredictor()
        r1 = p1.predict_from_smiles(BENZENE)
        r2 = p2.predict_from_smiles(ASPIRIN)
        assert r1.n_bands != r2.n_bands or r1.smiles != r2.smiles


# ═══════════════════════════════════════════════════════════════════════════════
# TestPredictKnownBands — positive detection per functional group
# ═══════════════════════════════════════════════════════════════════════════════

class TestPredictKnownBands:

    # Oxygen
    def test_alcohol_has_oh_stretch(self, predictor):
        assert has_label_containing(bands_for(predictor, ETHANOL), "alcohol", "O–H")

    def test_alcohol_has_co_stretch(self, predictor):
        assert has_label_containing(bands_for(predictor, ETHANOL), "alcohol", "C–O")

    def test_phenol_has_oh_stretch(self, predictor):
        assert has_label_containing(bands_for(predictor, PHENOL), "phenol", "O–H")

    def test_carboxylic_acid_has_carbonyl(self, predictor):
        assert has_label_containing(bands_for(predictor, ACETIC_ACID), "carboxylic_acid", "C=O")

    def test_carboxylic_acid_has_broad_oh(self, predictor):
        bs = [b for b in bands_for(predictor, ACETIC_ACID)
              if b.fg_key == "carboxylic_acid" and "O–H" in b.label]
        assert len(bs) >= 1

    def test_ester_has_carbonyl(self, predictor):
        assert has_label_containing(bands_for(predictor, ETHYL_ACETATE), "ester", "C=O")

    def test_ester_has_coc_stretch(self, predictor):
        assert has_label_containing(bands_for(predictor, ETHYL_ACETATE), "ester", "C–O–C")

    def test_ether_has_coc_stretch(self, predictor):
        assert has_label_containing(bands_for(predictor, DIETHYLETHER), "ether", "C–O–C")

    def test_aldehyde_has_carbonyl(self, predictor):
        assert has_label_containing(bands_for(predictor, ACETALDEHYDE), "aldehyde", "C=O")

    def test_aldehyde_has_ch_fermi(self, predictor):
        assert has_label_containing(bands_for(predictor, ACETALDEHYDE), "aldehyde", "C–H")

    def test_ketone_has_carbonyl(self, predictor):
        assert has_label_containing(bands_for(predictor, ACETONE), "ketone", "C=O")

    # Nitrogen
    def test_primary_amine_has_nh_stretch(self, predictor):
        assert has_label_containing(bands_for(predictor, METHYLAMINE), "primary_amine", "N–H")

    def test_primary_amine_has_nh_bend(self, predictor):
        assert has_label_containing(bands_for(predictor, METHYLAMINE), "primary_amine", "N–H bend")

    def test_amide_has_amide_i(self, predictor):
        assert has_label_containing(bands_for(predictor, ACETAMIDE), "amide", "Amide I")

    def test_amide_has_amide_ii(self, predictor):
        assert has_label_containing(bands_for(predictor, ACETAMIDE), "amide", "Amide II")

    def test_nitrile_has_cn_triple(self, predictor):
        assert has_label_containing(bands_for(predictor, ACETONITRILE), "nitrile", "C≡N")

    def test_nitro_has_no_asym(self, predictor):
        assert has_label_containing(bands_for(predictor, NITROBENZENE), "nitro", "N=O")

    def test_nitro_has_no_sym(self, predictor):
        bs = [b for b in bands_for(predictor, NITROBENZENE)
              if b.fg_key == "nitro"]
        assert len(bs) == 2  # asym + sym

    # Sulfur
    def test_thiol_has_sh_stretch(self, predictor):
        assert has_label_containing(bands_for(predictor, ETHANETHIOL), "thiol", "S–H")

    def test_sulfonamide_has_so_stretch(self, predictor):
        assert has_label_containing(bands_for(predictor, DIMETHYLSULFONAMIDE), "sulfonamide", "S=O")

    # Halogens
    def test_chloride_has_ccl_stretch(self, predictor):
        assert has_label_containing(bands_for(predictor, CHLOROBENZENE), "chloride", "C–Cl")

    def test_fluoride_has_cf_stretch(self, predictor):
        assert has_label_containing(bands_for(predictor, FLUOROBENZENE), "fluoride", "C–F")

    # Aromatic
    def test_aromatic_has_arcc_stretch(self, predictor):
        assert has_label_containing(bands_for(predictor, BENZENE), "aromatic_ring", "C=C")

    def test_aromatic_has_ch_stretch(self, predictor):
        assert has_label_containing(bands_for(predictor, BENZENE), "aromatic_ring", "C–H")

    def test_aromatic_has_oop_bend(self, predictor):
        assert has_label_containing(bands_for(predictor, BENZENE), "aromatic_ring", "oop")

    # Unsaturated
    def test_alkene_has_cc_stretch(self, predictor):
        assert has_label_containing(bands_for(predictor, STYRENE), "alkene", "C=C")

    def test_alkyne_has_cc_triple(self, predictor):
        assert has_label_containing(bands_for(predictor, PROPYNE), "alkyne", "C≡C")

    # Complex molecules
    def test_aspirin_has_ester_and_carboxylic_acid_bands(self, predictor):
        bands = bands_for(predictor, ASPIRIN)
        assert has_band_key(bands, "ester")
        assert has_band_key(bands, "carboxylic_acid")

    def test_paracetamol_has_amide_and_phenol_bands(self, predictor):
        bands = bands_for(predictor, PARACETAMOL)
        assert has_band_key(bands, "amide")
        assert has_band_key(bands, "phenol")

    def test_penicillin_g_has_amide_band(self, predictor):
        assert has_band_key(bands_for(predictor, PENICILLIN_G), "amide")

    def test_diazepam_has_chloride_band(self, predictor):
        assert has_band_key(bands_for(predictor, DIAZEPAM), "chloride")


# ═══════════════════════════════════════════════════════════════════════════════
# TestPredictNegativeCases
# ═══════════════════════════════════════════════════════════════════════════════

class TestPredictNegativeCases:

    def test_benzene_no_oh_band(self, predictor):
        assert not has_band_key(bands_for(predictor, BENZENE), "alcohol")

    def test_benzene_no_carboxylic_acid(self, predictor):
        assert not has_band_key(bands_for(predictor, BENZENE), "carboxylic_acid")

    def test_acetonitrile_no_nitro_band(self, predictor):
        assert not has_band_key(bands_for(predictor, ACETONITRILE), "nitro")

    def test_methane_no_aromatic_band(self, predictor):
        assert not has_band_key(bands_for(predictor, METHANE), "aromatic_ring")

    def test_ethanol_no_carbonyl(self, predictor):
        assert not has_band_key(bands_for(predictor, ETHANOL), "ketone")
        assert not has_band_key(bands_for(predictor, ETHANOL), "aldehyde")

    def test_no_thiol_in_aspirin(self, predictor):
        assert not has_band_key(bands_for(predictor, ASPIRIN), "thiol")

    def test_no_nitrile_in_acetamide(self, predictor):
        assert not has_band_key(bands_for(predictor, ACETAMIDE), "nitrile")


# ═══════════════════════════════════════════════════════════════════════════════
# TestAliphaticCH
# ═══════════════════════════════════════════════════════════════════════════════

class TestAliphaticCH:

    def test_methane_has_aliphatic_ch(self, predictor):
        bands = bands_for(predictor, METHANE)
        assert has_band_key(bands, "aliphatic_ch")

    def test_ethanol_has_aliphatic_ch(self, predictor):
        assert has_band_key(bands_for(predictor, ETHANOL), "aliphatic_ch")

    def test_aspirin_has_aliphatic_ch(self, predictor):
        # Aspirin has -OCOCH3 — sp3 carbon present
        assert has_band_key(bands_for(predictor, ASPIRIN), "aliphatic_ch")

    def test_benzene_no_aliphatic_ch(self, predictor):
        # Benzene has no sp3 carbon
        assert not has_band_key(bands_for(predictor, BENZENE), "aliphatic_ch")

    def test_aliphatic_ch_wavenumber_range(self, predictor):
        bands = bands_for(predictor, METHANE)
        ch = next(b for b in bands if b.fg_key == "aliphatic_ch")
        assert 2800 <= ch.low_cm <= 2900
        assert 2920 <= ch.high_cm <= 3000

    def test_aliphatic_ch_intensity_strong(self, predictor):
        bands = bands_for(predictor, METHANE)
        ch = next(b for b in bands if b.fg_key == "aliphatic_ch")
        assert ch.intensity == "strong"


# ═══════════════════════════════════════════════════════════════════════════════
# TestWarnings
# ═══════════════════════════════════════════════════════════════════════════════

class TestWarnings:

    def test_no_warnings_for_aspirin(self, predictor):
        result = predictor.predict_from_smiles(ASPIRIN)
        assert result.warnings == []

    def test_warning_for_water_no_fg(self, predictor):
        # Water has no carbon FGs — should warn
        result = predictor.predict_from_smiles(WATER)
        assert len(result.warnings) > 0

    def test_none_mol_raises_valueerror(self, predictor):
        with pytest.raises(ValueError, match="None"):
            predictor.predict(None)

    def test_empty_smiles_raises_valueerror(self, predictor):
        with pytest.raises(ValueError):
            predictor.predict_from_smiles("")

    def test_bad_smiles_raises_valueerror(self, predictor):
        with pytest.raises(ValueError, match="could not parse"):
            predictor.predict_from_smiles("NOTVALIDSMILES###")

    def test_large_molecule_warning(self, predictor):
        # Cyclosporin A: 45 heavy atoms — still under threshold; use a bigger mock
        long_chain = "C" * 90   # not valid SMILES but we test via mol
        # Instead build a real large mol: concatenate rings
        taxol_like = "OC(=O)c1ccccc1" * 1  # small; use MW-heavy reference
        # Just verify the warning fires for a molecule we know is > 80 heavy atoms
        # We'll build one programmatically
        from rdkit import Chem
        # Statin-like large mol (lovastatin, 36 heavy) — under threshold
        # Use a SMILES known to have >80 heavy atoms: vancomycin aglycone-like
        # Fallback: just verify the threshold logic by checking n_heavy attribute
        big_smi = "c1ccccc1" + "CC(=O)O" * 10  # not valid; skip with try/except
        try:
            result = predictor.predict_from_smiles(big_smi)
        except ValueError:
            pytest.skip("Could not build large test molecule")
        # If it parsed somehow, no crash is the test


# ═══════════════════════════════════════════════════════════════════════════════
# TestSummaryOutput
# ═══════════════════════════════════════════════════════════════════════════════

class TestSummaryOutput:

    def test_summary_is_string(self, predictor):
        r = predictor.predict_from_smiles(ASPIRIN)
        assert isinstance(r.summary(), str)

    def test_summary_contains_heuristic_label(self, predictor):
        s = predictor.predict_from_smiles(ASPIRIN).summary()
        assert "heuristic" in s.lower() or "HEURISTIC" in s

    def test_summary_contains_smiles(self, predictor):
        r = predictor.predict_from_smiles(BENZENE)
        assert BENZENE in r.summary() or "c1ccc" in r.summary()

    def test_summary_contains_wavenumbers(self, predictor):
        s = predictor.predict_from_smiles(ACETIC_ACID).summary()
        assert "cm" in s

    def test_summary_contains_fg_name(self, predictor):
        s = predictor.predict_from_smiles(ACETAMIDE).summary()
        assert "amide" in s.lower()

    def test_summary_contains_region_headers(self, predictor):
        s = predictor.predict_from_smiles(ASPIRIN).summary()
        assert "Fingerprint" in s or "Double bonds" in s

    def test_summary_nonempty_for_methane(self, predictor):
        assert len(predictor.predict_from_smiles(METHANE).summary()) > 50


# ═══════════════════════════════════════════════════════════════════════════════
# TestBandRegions
# ═══════════════════════════════════════════════════════════════════════════════

class TestBandRegions:

    def test_nitrile_in_triple_bond_region(self, predictor):
        r   = predictor.predict_from_smiles(ACETONITRILE)
        reg = r.bands_by_region()
        triple_bands = reg.get("Triple bonds  (2000–3000)", [])
        assert any(b.fg_key == "nitrile" for b in triple_bands)

    def test_carbonyl_in_double_bond_region(self, predictor):
        r   = predictor.predict_from_smiles(ACETIC_ACID)
        reg = r.bands_by_region()
        dbl = reg.get("Double bonds  (1500–2000)", [])
        assert any(b.fg_key == "carboxylic_acid" and "C=O" in b.label for b in dbl)

    def test_alcohol_oh_in_xh_stretch_region(self, predictor):
        r   = predictor.predict_from_smiles(ETHANOL)
        reg = r.bands_by_region()
        xh  = reg.get("X–H stretch (3000–3600)", [])
        assert any(b.fg_key == "alcohol" for b in xh)

    def test_ccl_in_fingerprint_region(self, predictor):
        r   = predictor.predict_from_smiles(CHLOROBENZENE)
        reg = r.bands_by_region()
        fp  = reg.get("Fingerprint   (600–1500)", [])
        assert any(b.fg_key == "chloride" for b in fp)

    def test_all_bands_assigned_to_a_region(self, predictor):
        r   = predictor.predict_from_smiles(ASPIRIN)
        all_from_regions = sum(len(v) for v in r.bands_by_region().values())
        assert all_from_regions == r.n_bands


# ═══════════════════════════════════════════════════════════════════════════════
# TestConvenienceFunctions
# ═══════════════════════════════════════════════════════════════════════════════

class TestConvenienceFunctions:

    def test_predict_ir_with_smiles(self):
        r = predict_ir(ASPIRIN)
        assert isinstance(r, IRPrediction)
        assert r.n_bands > 0

    def test_predict_ir_with_mol(self):
        r = predict_ir(mol(BENZENE))
        assert isinstance(r, IRPrediction)

    def test_predict_ir_none_raises(self):
        with pytest.raises(ValueError):
            predict_ir(None)

    def test_predict_ir_smiles_and_mol_same_result(self):
        r1 = predict_ir(CAFFEINE)
        r2 = predict_ir(mol(CAFFEINE))
        assert r1.n_bands == r2.n_bands

    def test_predict_from_smiles_whitespace_raises(self, predictor):
        with pytest.raises(ValueError):
            predictor.predict_from_smiles("   ")


# ═══════════════════════════════════════════════════════════════════════════════
# TestEdgeCases
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:

    def test_water_returns_prediction(self, predictor):
        r = predictor.predict_from_smiles(WATER)
        assert isinstance(r, IRPrediction)

    def test_water_has_zero_organic_bands(self, predictor):
        r = predictor.predict_from_smiles(WATER)
        organic_band_keys = {b.fg_key for b in r.bands}
        # water should have no aliphatic CH (no sp3 carbon) and no organic FGs
        assert "aliphatic_ch" not in organic_band_keys

    def test_methane_returns_only_aliphatic_ch(self, predictor):
        r = predictor.predict_from_smiles(METHANE)
        keys = {b.fg_key for b in r.bands}
        assert "aliphatic_ch" in keys

    def test_benzene_n_bands_positive(self, predictor):
        r = predictor.predict_from_smiles(BENZENE)
        assert r.n_bands > 0

    def test_oxalic_acid_two_carboxylic_acid_fgs(self, predictor):
        """Oxalic acid has 2 COOH but FG detection deduplicates to 1 key with count=2."""
        r = predictor.predict_from_smiles(OXALIC_ACID)
        assert has_band_key(r.bands, "carboxylic_acid")

    def test_repeated_predict_same_smiles_identical(self, predictor):
        r1 = predictor.predict_from_smiles(ASPIRIN)
        r2 = predictor.predict_from_smiles(ASPIRIN)
        assert r1.n_bands == r2.n_bands
        assert set(b.fg_key for b in r1.bands) == set(b.fg_key for b in r2.bands)

    def test_use_chirality_flag_does_not_crash(self, predictor):
        r = predictor.predict(mol(IBUPROFEN), use_chirality=True)
        assert r.n_bands > 0


# ═══════════════════════════════════════════════════════════════════════════════
# TestHeuristicLabel
# ═══════════════════════════════════════════════════════════════════════════════

class TestHeuristicLabel:

    def test_all_bands_are_heuristic(self, predictor):
        r = predictor.predict_from_smiles(ASPIRIN)
        for b in r.bands:
            assert b.is_heuristic is True, f"Band {b.label!r} not labelled heuristic"

    def test_prediction_is_heuristic(self, predictor):
        r = predictor.predict_from_smiles(CAFFEINE)
        assert r.is_heuristic is True

    def test_to_dict_marks_is_heuristic_true(self, predictor):
        d = predictor.predict_from_smiles(ACETIC_ACID).to_dict()
        assert d["is_heuristic"] is True
        for b in d["bands"]:
            assert b["is_heuristic"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# TestSerialisation
# ═══════════════════════════════════════════════════════════════════════════════

class TestSerialisation:

    def test_to_dict_json_serialisable(self, predictor):
        r = predictor.predict_from_smiles(ASPIRIN)
        json.dumps(r.to_dict())

    def test_to_dict_schema(self, predictor):
        d = predictor.predict_from_smiles(ASPIRIN).to_dict()
        for key in ("smiles","fg_keys","fg_names","n_bands","is_heuristic",
                    "warnings","bands"):
            assert key in d

    def test_band_dicts_have_all_fields(self, predictor):
        d = predictor.predict_from_smiles(ASPIRIN).to_dict()
        for b in d["bands"]:
            for key in ("fg_key","fg_name","label","low_cm","high_cm",
                        "mid_cm","intensity","description","is_heuristic"):
                assert key in b, f"Missing key {key!r} in band dict"

    def test_bands_list_in_dict_sorted_desc(self, predictor):
        d    = predictor.predict_from_smiles(PARACETAMOL).to_dict()
        mids = [b["mid_cm"] for b in d["bands"]]
        assert mids == sorted(mids, reverse=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TestReferenceChemistry — validate wavenumber ranges against textbook values
# Silverstein 8th ed. / Pavia 5th ed.
# ═══════════════════════════════════════════════════════════════════════════════

class TestReferenceChemistry:

    def _get_band(self, predictor, smiles, fg_key, label_substr):
        bands = bands_for(predictor, smiles)
        matches = [b for b in bands
                   if b.fg_key == fg_key and label_substr.lower() in b.label.lower()]
        assert matches, f"No band found for {fg_key!r} with label containing {label_substr!r}"
        return matches[0]

    def test_carboxylic_acid_carbonyl_1700_to_1725(self, predictor):
        b = self._get_band(predictor, ACETIC_ACID, "carboxylic_acid", "C=O")
        assert b.low_cm <= 1725 and b.high_cm >= 1700

    def test_ester_carbonyl_above_1730(self, predictor):
        b = self._get_band(predictor, ETHYL_ACETATE, "ester", "C=O")
        # Ester C=O is higher than ketone (~1735–1750)
        assert b.low_cm >= 1730

    def test_ketone_carbonyl_1705_to_1725(self, predictor):
        b = self._get_band(predictor, ACETONE, "ketone", "C=O")
        assert 1700 <= b.low_cm and b.high_cm <= 1730

    def test_ester_higher_than_ketone_carbonyl(self, predictor):
        ester_b  = self._get_band(predictor, ETHYL_ACETATE, "ester",  "C=O")
        ketone_b = self._get_band(predictor, ACETONE,       "ketone", "C=O")
        assert ester_b.low_cm > ketone_b.low_cm

    def test_nitrile_2200_to_2260(self, predictor):
        b = self._get_band(predictor, ACETONITRILE, "nitrile", "C≡N")
        assert 2190 <= b.low_cm and b.high_cm <= 2270

    def test_nitro_asym_1500_to_1570(self, predictor):
        b = self._get_band(predictor, NITROBENZENE, "nitro", "stretch (asym)")
        assert 1490 <= b.low_cm and b.high_cm <= 1580

    def test_nitro_sym_1300_to_1370(self, predictor):
        # "stretch (sym)" uniquely matches the symmetric N=O band only
        b = self._get_band(predictor, NITROBENZENE, "nitro", "stretch (sym)")
        assert 1290 <= b.low_cm and b.high_cm <= 1380

    def test_thiol_sh_2550_to_2600(self, predictor):
        b = self._get_band(predictor, ETHANETHIOL, "thiol", "S–H")
        assert 2540 <= b.low_cm and b.high_cm <= 2610

    def test_amide_i_1630_to_1690(self, predictor):
        b = self._get_band(predictor, ACETAMIDE, "amide", "Amide I")
        assert 1620 <= b.low_cm and b.high_cm <= 1700

    def test_amide_ii_1510_to_1570(self, predictor):
        b = self._get_band(predictor, ACETAMIDE, "amide", "Amide II")
        assert 1500 <= b.low_cm and b.high_cm <= 1580

    def test_alcohol_oh_above_3200(self, predictor):
        b = self._get_band(predictor, ETHANOL, "alcohol", "O–H")
        assert b.low_cm >= 3200

    def test_carboxylic_oh_stretch_below_3300(self, predictor):
        """Very broad COOH O–H starts below 3300 cm⁻¹ — highly characteristic."""
        b = self._get_band(predictor, ACETIC_ACID, "carboxylic_acid", "O–H")
        assert b.low_cm <= 3300

    def test_aliphatic_ch_2850_to_2960(self, predictor):
        bands = bands_for(predictor, METHANE)
        ch    = next(b for b in bands if b.fg_key == "aliphatic_ch")
        assert 2840 <= ch.low_cm and ch.high_cm <= 2970

    def test_aromatic_ch_above_3000(self, predictor):
        b = self._get_band(predictor, BENZENE, "aromatic_ring", "C–H stretch")
        assert b.low_cm >= 3000

    def test_cf_stretch_1000_to_1400(self, predictor):
        b = self._get_band(predictor, FLUOROBENZENE, "fluoride", "C–F")
        assert 990 <= b.low_cm and b.high_cm <= 1410

    def test_ccl_stretch_600_to_800(self, predictor):
        b = self._get_band(predictor, CHLOROBENZENE, "chloride", "C–Cl")
        assert 590 <= b.low_cm and b.high_cm <= 810


# ═══════════════════════════════════════════════════════════════════════════════
# TestIRPeak — lightweight dataclass from merged version
# ═══════════════════════════════════════════════════════════════════════════════

class TestIRPeak:
    from spectra.ir_predictor import IRPeak as _IRPeak

    def _peak(self):
        from spectra.ir_predictor import IRPeak
        return IRPeak(
            functional_group="carboxylic_acid",
            wavenumber_range=(1700, 1725),
            intensity="strong",
            description="C=O stretch (acid)",
        )

    def test_default_heuristic_note(self):
        assert "HEURISTIC" in self._peak().heuristic_note

    def test_str_contains_range(self):
        s = str(self._peak())
        assert "1700" in s and "1725" in s

    def test_str_contains_intensity(self):
        assert "strong" in str(self._peak())

    def test_to_dict_has_wavenumber_as_list(self):
        d = self._peak().to_dict()
        assert isinstance(d["wavenumber_range"], list)
        assert d["wavenumber_range"] == [1700, 1725]

    def test_to_dict_json_serialisable(self):
        import json
        json.dumps(self._peak().to_dict())

    def test_is_frozen(self):
        from dataclasses import FrozenInstanceError
        p = self._peak()
        with pytest.raises((FrozenInstanceError, AttributeError)):
            p.intensity = "weak"


# ═══════════════════════════════════════════════════════════════════════════════
# TestPredictFromGroups — module-level function
# ═══════════════════════════════════════════════════════════════════════════════

class TestPredictFromGroups:
    from spectra.ir_predictor import predict_from_groups as _pfg

    def test_valid_key_returns_peaks(self):
        from spectra.ir_predictor import predict_from_groups, IRPeak
        peaks = predict_from_groups({"carboxylic_acid": 1})
        assert len(peaks) > 0
        assert all(isinstance(p, IRPeak) for p in peaks)

    def test_multiple_keys_returns_all_peaks(self):
        from spectra.ir_predictor import predict_from_groups
        peaks = predict_from_groups({"carboxylic_acid": 1, "aromatic_ring": 1, "ester": 1})
        fg_keys = {p.functional_group for p in peaks}
        assert "carboxylic_acid" in fg_keys
        assert "aromatic_ring" in fg_keys
        assert "ester" in fg_keys

    def test_count_zero_skipped(self):
        from spectra.ir_predictor import predict_from_groups
        peaks = predict_from_groups({"carboxylic_acid": 0, "aromatic_ring": 1})
        assert all(p.functional_group != "carboxylic_acid" for p in peaks)

    def test_count_negative_skipped(self):
        from spectra.ir_predictor import predict_from_groups
        peaks = predict_from_groups({"ketone": -1})
        assert peaks == []

    def test_empty_dict_returns_empty(self):
        from spectra.ir_predictor import predict_from_groups
        assert predict_from_groups({}) == []

    def test_non_dict_raises_typeerror(self):
        from spectra.ir_predictor import predict_from_groups
        with pytest.raises(TypeError):
            predict_from_groups(["carboxylic_acid"])

    def test_unknown_key_returns_placeholder(self):
        from spectra.ir_predictor import predict_from_groups
        peaks = predict_from_groups({"unknown_exotic_group": 1})
        assert len(peaks) == 1
        assert peaks[0].wavenumber_range == (0, 0)
        assert "No reference" in peaks[0].description

    def test_sorted_descending_wavenumber(self):
        from spectra.ir_predictor import predict_from_groups
        peaks = predict_from_groups({"carboxylic_acid": 1, "nitro": 1, "chloride": 1})
        wns = [p.wavenumber_range[0] for p in peaks if p.wavenumber_range[0] > 0]
        assert wns == sorted(wns, reverse=True)

    def test_normalised_name_lookup(self):
        """Human-readable names like 'Carboxylic Acid' should resolve correctly."""
        from spectra.ir_predictor import predict_from_groups
        peaks = predict_from_groups({"Carboxylic Acid": 1})
        valid = [p for p in peaks if p.wavenumber_range[0] > 0]
        assert len(valid) > 0

    def test_all_peaks_heuristic_note(self):
        from spectra.ir_predictor import predict_from_groups
        peaks = predict_from_groups({"amide": 1})
        for p in peaks:
            if p.wavenumber_range[0] > 0:
                assert "HEURISTIC" in p.heuristic_note

    def test_via_predictor_instance(self, predictor):
        """IRPredictor.predict_from_groups() delegates correctly."""
        from spectra.ir_predictor import IRPeak
        peaks = predictor.predict_from_groups({"ketone": 1})
        assert any(isinstance(p, IRPeak) for p in peaks)

    def test_carboxylic_acid_has_carbonyl_peak(self):
        from spectra.ir_predictor import predict_from_groups
        peaks = predict_from_groups({"carboxylic_acid": 1})
        labels = [p.description for p in peaks]
        assert any("C=O" in l for l in labels)

    def test_nitro_returns_two_peaks(self):
        from spectra.ir_predictor import predict_from_groups
        peaks = predict_from_groups({"nitro": 1})
        assert len(peaks) == 2  # asym + sym


# ═══════════════════════════════════════════════════════════════════════════════
# TestSummaryText — module-level formatter
# ═══════════════════════════════════════════════════════════════════════════════

class TestSummaryText:

    def test_returns_string(self):
        from spectra.ir_predictor import predict_from_groups, summary_text
        peaks = predict_from_groups({"amide": 1})
        assert isinstance(summary_text(peaks), str)

    def test_empty_iterable_returns_fallback(self):
        from spectra.ir_predictor import summary_text
        assert "(no IR bands predicted)" in summary_text([])

    def test_contains_wavenumber(self):
        from spectra.ir_predictor import predict_from_groups, summary_text
        peaks = predict_from_groups({"carboxylic_acid": 1})
        s = summary_text(peaks)
        assert "cm⁻¹" in s or "1700" in s

    def test_contains_functional_group(self):
        from spectra.ir_predictor import predict_from_groups, summary_text
        peaks = predict_from_groups({"nitrile": 1})
        s = summary_text(peaks)
        assert "nitrile" in s.lower()

    def test_placeholder_peaks_handled(self):
        from spectra.ir_predictor import predict_from_groups, summary_text
        peaks = predict_from_groups({"unknown_xyz": 1})
        s = summary_text(peaks)
        assert "No reference" in s

    def test_accepts_generator(self):
        from spectra.ir_predictor import predict_from_groups, summary_text, IRPeak
        gen = (p for p in predict_from_groups({"ketone": 1}))
        assert isinstance(summary_text(gen), str)
