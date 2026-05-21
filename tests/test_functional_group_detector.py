"""
chemistry_companion/tests/test_functional_group_detector.py
============================================================
Comprehensive tests for spectra/functional_group_detector.py

Run:
    python -m pytest tests/test_functional_group_detector.py -v --tb=short

Test groups:
    TestRegistry              — FGDefinition structure, registry integrity
    TestDetectorInit          — compile behaviour, registry introspection
    TestKnownFunctionalGroups — per-group detection on canonical reference molecules
    TestNegativeCases         — groups that MUST NOT fire on specific molecules
    TestReportAPI             — FGReport methods (.has, .get, .names, .summary)
    TestCustomRegistry        — register_custom_group(), runtime extension
    TestEdgeCases             — None mol, bad SMILES, empty molecule, chirality flag
    TestBatchConsistency      — same results across repeated detect() calls
"""

import logging
import sys, os
import pytest
from rdkit import Chem

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spectra.functional_group_detector import (
    FGDefinition,
    FGMatch,
    FGReport,
    FunctionalGroupDetector,
    FUNCTIONAL_GROUP_REGISTRY,
    detect_functional_groups,
    register_custom_group,
    get_registry,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def detector():
    """Shared detector instance — compiled once per test session."""
    return FunctionalGroupDetector()


def mol(smiles: str) -> Chem.Mol:
    """Helper: parse SMILES, fail immediately on bad input."""
    m = Chem.MolFromSmiles(smiles)
    assert m is not None, f"Test setup failed — bad SMILES: {smiles!r}"
    return m


# ── Reference molecules ───────────────────────────────────────────────────────

ASPIRIN     = "CC(=O)Oc1ccccc1C(=O)O"
CAFFEINE    = "Cn1cnc2c1c(=O)n(c(=O)n2C)C"
BENZENE     = "c1ccccc1"
ETHANOL     = "CCO"
PHENOL      = "Oc1ccccc1"
ACETIC_ACID = "CC(=O)O"
ETHYL_ACETATE = "CCOC(=O)C"
DIETHYL_ETHER = "CCOCC"
ACETALDEHYDE  = "CC=O"
ACETONE       = "CC(C)=O"
METHYLAMINE   = "CN"
DIMETHYLAMINE = "CNC"
TRIETHYLAMINE = "CCN(CC)CC"
ACETAMIDE     = "CC(=O)N"
ACETONITRILE  = "CC#N"
NITROBENZENE  = "O=[N+]([O-])c1ccccc1"
CHLOROBENZENE = "Clc1ccccc1"
FLUOROBENZENE = "Fc1ccccc1"
BROMOBENZENE  = "Brc1ccccc1"
IODOBENZENE   = "Ic1ccccc1"
ETHANETHIOL   = "CCS"
DIMETHYLSULFIDE = "CSC"
METHANESULFONAMIDE = "CS(=O)(=O)N"
STYRENE       = "C=Cc1ccccc1"
PROPYNE       = "CC#C"
PARACETAMOL   = "CC(=O)Nc1ccc(O)cc1"
IBUPROFEN     = "CC(C)Cc1ccc(cc1)[C@@H](C)C(=O)O"
PENICILLIN_G  = "CC1(C)SC2C(NC(=O)Cc3ccccc3)C(=O)N2C1C(=O)O"
DIAZEPAM      = "CN1C(=O)CN=C(c2ccccc2)c2cc(Cl)ccc21"
GUANIDINE_SMI = "NC(=N)N"
EPOXIDE_SMI   = "C1CO1"
TRIMETHYLPHOSPHATE = "COP(=O)(OC)OC"


# ═══════════════════════════════════════════════════════════════════════════════
# TestRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegistry:

    def test_registry_is_nonempty(self):
        assert len(FUNCTIONAL_GROUP_REGISTRY) > 0

    def test_all_entries_are_fgdefinition(self):
        for key, val in FUNCTIONAL_GROUP_REGISTRY.items():
            assert isinstance(val, FGDefinition), f"Bad type for key {key!r}"

    def test_all_names_nonempty(self):
        for key, defn in FUNCTIONAL_GROUP_REGISTRY.items():
            assert defn.name.strip(), f"Empty name for key {key!r}"

    def test_all_smarts_strings_nonempty(self):
        for key, defn in FUNCTIONAL_GROUP_REGISTRY.items():
            assert defn.smarts.strip(), f"Empty SMARTS for key {key!r}"

    def test_all_categories_nonempty(self):
        for key, defn in FUNCTIONAL_GROUP_REGISTRY.items():
            assert defn.category.strip(), f"Empty category for key {key!r}"

    def test_all_smarts_compile(self):
        """Every SMARTS in the registry must compile without error."""
        failed = []
        for key, defn in FUNCTIONAL_GROUP_REGISTRY.items():
            if Chem.MolFromSmarts(defn.smarts) is None:
                failed.append(key)
        assert failed == [], f"SMARTS compile failures: {failed}"

    def test_ir_bands_are_tuples(self):
        for key, defn in FUNCTIONAL_GROUP_REGISTRY.items():
            for band in defn.ir_bands:
                assert len(band) == 3, f"IR band for {key!r} must have 3 elements"
                label, lo, hi = band
                assert isinstance(label, str)
                assert isinstance(lo, int) and isinstance(hi, int)
                assert lo < hi, f"IR band lo >= hi for {key!r}: {band}"

    def test_priority_values_are_positive(self):
        for key, defn in FUNCTIONAL_GROUP_REGISTRY.items():
            assert defn.priority > 0, f"Priority must be > 0 for {key!r}"

    def test_get_registry_returns_dict(self):
        reg = get_registry()
        assert isinstance(reg, dict) and len(reg) > 0

    def test_known_keys_present(self):
        required = {
            "alcohol", "phenol", "carboxylic_acid", "ester", "ether",
            "aldehyde", "ketone", "primary_amine", "secondary_amine",
            "tertiary_amine", "amide", "nitrile", "nitro",
            "aromatic_ring", "sulfonamide", "thiol",
            "fluoride", "chloride", "bromide", "iodide",
        }
        for key in required:
            assert key in FUNCTIONAL_GROUP_REGISTRY, f"Missing key: {key!r}"


# ═══════════════════════════════════════════════════════════════════════════════
# TestDetectorInit
# ═══════════════════════════════════════════════════════════════════════════════

class TestDetectorInit:

    def test_default_registry_size_matches_module_constant(self, detector):
        assert detector.registry_size == len(FUNCTIONAL_GROUP_REGISTRY)

    def test_available_categories_nonempty(self, detector):
        cats = detector.available_categories
        assert len(cats) > 0 and isinstance(cats, list)

    def test_known_categories_present(self, detector):
        for cat in ("oxygen", "nitrogen", "halogen", "sulfur", "aromatic"):
            assert cat in detector.available_categories

    def test_registry_summary_is_string(self, detector):
        s = detector.registry_summary()
        assert isinstance(s, str) and len(s) > 50

    def test_custom_registry_isolates_from_default(self):
        """Custom registry must not mutate FUNCTIONAL_GROUP_REGISTRY."""
        before = len(FUNCTIONAL_GROUP_REGISTRY)
        custom = register_custom_group(
            "test_dummy",
            FGDefinition(
                name="Test Dummy", smarts="[CH4]",
                category="test", description="Methane test pattern.",
            ),
        )
        assert len(FUNCTIONAL_GROUP_REGISTRY) == before
        assert "test_dummy" in custom

    def test_bad_smarts_in_custom_registry_skipped_gracefully(self):
        """A bad SMARTS must not crash __init__ — it should be skipped."""
        custom = dict(FUNCTIONAL_GROUP_REGISTRY)
        custom["bad_pattern"] = FGDefinition(
            name="Bad",
            smarts="[[[NOTVALID",
            category="test",
            description="Intentionally broken SMARTS.",
        )
        # Should not raise; bad pattern ends up in failed_patterns
        d = FunctionalGroupDetector(registry=custom)
        assert d.registry_size == len(custom)


# ═══════════════════════════════════════════════════════════════════════════════
# TestKnownFunctionalGroups — positive detection tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestKnownFunctionalGroups:

    # Oxygen groups
    def test_alcohol_in_ethanol(self, detector):
        r = detector.detect(mol(ETHANOL)); assert r.has("alcohol")

    def test_phenol_in_phenol(self, detector):
        r = detector.detect(mol(PHENOL)); assert r.has("phenol")

    def test_carboxylic_acid_in_acetic_acid(self, detector):
        r = detector.detect(mol(ACETIC_ACID)); assert r.has("carboxylic_acid")

    def test_carboxylic_acid_in_aspirin(self, detector):
        r = detector.detect(mol(ASPIRIN)); assert r.has("carboxylic_acid")

    def test_ester_in_ethyl_acetate(self, detector):
        r = detector.detect(mol(ETHYL_ACETATE)); assert r.has("ester")

    def test_ester_in_aspirin(self, detector):
        r = detector.detect(mol(ASPIRIN)); assert r.has("ester")

    def test_ether_in_diethyl_ether(self, detector):
        r = detector.detect(mol(DIETHYL_ETHER)); assert r.has("ether")

    def test_aldehyde_in_acetaldehyde(self, detector):
        r = detector.detect(mol(ACETALDEHYDE)); assert r.has("aldehyde")

    def test_ketone_in_acetone(self, detector):
        r = detector.detect(mol(ACETONE)); assert r.has("ketone")

    def test_epoxide_detected(self, detector):
        r = detector.detect(mol(EPOXIDE_SMI)); assert r.has("epoxide")

    # Nitrogen groups
    def test_primary_amine_in_methylamine(self, detector):
        r = detector.detect(mol(METHYLAMINE)); assert r.has("primary_amine")

    def test_secondary_amine_in_dimethylamine(self, detector):
        r = detector.detect(mol(DIMETHYLAMINE)); assert r.has("secondary_amine")

    def test_tertiary_amine_in_triethylamine(self, detector):
        r = detector.detect(mol(TRIETHYLAMINE)); assert r.has("tertiary_amine")

    def test_amide_in_acetamide(self, detector):
        r = detector.detect(mol(ACETAMIDE)); assert r.has("amide")

    def test_amide_in_paracetamol(self, detector):
        r = detector.detect(mol(PARACETAMOL)); assert r.has("amide")

    def test_nitrile_in_acetonitrile(self, detector):
        r = detector.detect(mol(ACETONITRILE)); assert r.has("nitrile")

    def test_nitro_in_nitrobenzene(self, detector):
        r = detector.detect(mol(NITROBENZENE)); assert r.has("nitro")

    def test_imine_in_diazepam(self, detector):
        r = detector.detect(mol(DIAZEPAM)); assert r.has("imine")

    def test_guanidine_detected(self, detector):
        r = detector.detect(mol(GUANIDINE_SMI)); assert r.has("guanidine")

    # Sulfur groups
    def test_thiol_in_ethanethiol(self, detector):
        r = detector.detect(mol(ETHANETHIOL)); assert r.has("thiol")

    def test_thioether_in_dimethylsulfide(self, detector):
        r = detector.detect(mol(DIMETHYLSULFIDE)); assert r.has("thioether")

    def test_sulfonamide_in_methanesulfonamide(self, detector):
        r = detector.detect(mol(METHANESULFONAMIDE)); assert r.has("sulfonamide")

    # Halogens
    def test_chloride_in_chlorobenzene(self, detector):
        r = detector.detect(mol(CHLOROBENZENE)); assert r.has("chloride")

    def test_fluoride_in_fluorobenzene(self, detector):
        r = detector.detect(mol(FLUOROBENZENE)); assert r.has("fluoride")

    def test_bromide_in_bromobenzene(self, detector):
        r = detector.detect(mol(BROMOBENZENE)); assert r.has("bromide")

    def test_iodide_in_iodobenzene(self, detector):
        r = detector.detect(mol(IODOBENZENE)); assert r.has("iodide")

    def test_chloride_in_diazepam(self, detector):
        r = detector.detect(mol(DIAZEPAM)); assert r.has("chloride")

    # Aromatic and unsaturated
    def test_aromatic_ring_in_benzene(self, detector):
        r = detector.detect(mol(BENZENE)); assert r.has("aromatic_ring")

    def test_aromatic_ring_in_aspirin(self, detector):
        r = detector.detect(mol(ASPIRIN)); assert r.has("aromatic_ring")

    def test_alkene_in_styrene(self, detector):
        r = detector.detect(mol(STYRENE)); assert r.has("alkene")

    def test_alkyne_in_propyne(self, detector):
        r = detector.detect(mol(PROPYNE)); assert r.has("alkyne")

    # Phosphorus
    def test_phosphate_in_trimethylphosphate(self, detector):
        r = detector.detect(mol(TRIMETHYLPHOSPHATE)); assert r.has("phosphate")

    # Multi-group complex molecules
    def test_aspirin_has_ester_and_carboxylic_acid(self, detector):
        r = detector.detect(mol(ASPIRIN))
        assert r.has("ester") and r.has("carboxylic_acid")

    def test_paracetamol_has_amide_and_phenol(self, detector):
        r = detector.detect(mol(PARACETAMOL))
        assert r.has("amide") and r.has("phenol")

    def test_ibuprofen_has_carboxylic_acid_and_aromatic(self, detector):
        r = detector.detect(mol(IBUPROFEN))
        assert r.has("carboxylic_acid") and r.has("aromatic_ring")

    def test_penicillin_g_has_amide_and_thioether(self, detector):
        r = detector.detect(mol(PENICILLIN_G))
        assert r.has("amide") and r.has("thioether")


# ═══════════════════════════════════════════════════════════════════════════════
# TestNegativeCases — groups that MUST NOT fire
# ═══════════════════════════════════════════════════════════════════════════════

class TestNegativeCases:

    def test_no_nitro_in_benzene(self, detector):
        r = detector.detect(mol(BENZENE)); assert not r.has("nitro")

    def test_no_thiol_in_benzene(self, detector):
        r = detector.detect(mol(BENZENE)); assert not r.has("thiol")

    def test_no_halogen_in_aspirin(self, detector):
        r = detector.detect(mol(ASPIRIN))
        assert not any(r.has(k) for k in ("fluoride","chloride","bromide","iodide"))

    def test_no_nitrile_in_acetamide(self, detector):
        r = detector.detect(mol(ACETAMIDE)); assert not r.has("nitrile")

    def test_no_aromatic_in_ethanol(self, detector):
        r = detector.detect(mol(ETHANOL)); assert not r.has("aromatic_ring")

    def test_no_alcohol_in_benzene(self, detector):
        r = detector.detect(mol(BENZENE)); assert not r.has("alcohol")

    def test_no_sulfonamide_in_dimethylsulfide(self, detector):
        r = detector.detect(mol(DIMETHYLSULFIDE)); assert not r.has("sulfonamide")


# ═══════════════════════════════════════════════════════════════════════════════
# TestReportAPI
# ═══════════════════════════════════════════════════════════════════════════════

class TestReportAPI:

    def test_report_has_correct_smiles(self, detector):
        r = detector.detect(mol(BENZENE))
        assert r.smiles  # non-empty

    def test_report_names_is_list_of_strings(self, detector):
        r = detector.detect(mol(ASPIRIN))
        assert isinstance(r.names, list)
        assert all(isinstance(n, str) for n in r.names)

    def test_report_keys_is_list_of_strings(self, detector):
        r = detector.detect(mol(ASPIRIN))
        assert isinstance(r.keys, list)
        assert all(isinstance(k, str) for k in r.keys)

    def test_report_has_returns_true_for_detected(self, detector):
        r = detector.detect(mol(ACETIC_ACID))
        assert r.has("carboxylic_acid") is True

    def test_report_has_returns_false_for_absent(self, detector):
        r = detector.detect(mol(BENZENE))
        assert r.has("carboxylic_acid") is False

    def test_report_get_returns_fgmatch(self, detector):
        r = detector.detect(mol(ASPIRIN))
        m = r.get("carboxylic_acid")
        assert isinstance(m, FGMatch)
        assert m.key == "carboxylic_acid"
        assert m.count >= 1

    def test_report_get_returns_none_when_absent(self, detector):
        r = detector.detect(mol(BENZENE))
        assert r.get("carboxylic_acid") is None

    def test_fgmatch_atom_indices_are_tuples(self, detector):
        r = detector.detect(mol(ASPIRIN))
        m = r.get("aromatic_ring")
        assert m is not None
        assert isinstance(m.atom_indices, tuple)
        assert all(isinstance(idx, tuple) for idx in m.atom_indices)

    def test_fgmatch_to_dict_serialisable(self, detector):
        import json
        r = detector.detect(mol(ASPIRIN))
        m = r.get("ester")
        d = m.to_dict()
        # must be JSON serialisable
        json.dumps(d)
        assert "key"          in d
        assert "atom_indices" in d
        assert "ir_bands"     in d

    def test_report_by_category_grouping(self, detector):
        r = detector.detect(mol(ASPIRIN))
        assert "oxygen"   in r.by_category
        assert "aromatic" in r.by_category

    def test_report_total_groups_positive(self, detector):
        r = detector.detect(mol(ASPIRIN))
        assert r.total_groups > 0

    def test_report_summary_is_string(self, detector):
        r = detector.detect(mol(ASPIRIN))
        s = r.summary()
        assert isinstance(s, str) and len(s) > 20

    def test_report_no_failed_patterns_for_valid_mol(self, detector):
        r = detector.detect(mol(ETHANOL))
        assert r.failed_patterns == []

    def test_detect_from_smiles_matches_detect_mol(self, detector):
        r1 = detector.detect(mol(ASPIRIN))
        r2 = detector.detect_from_smiles(ASPIRIN)
        assert set(r1.keys) == set(r2.keys)


# ═══════════════════════════════════════════════════════════════════════════════
# TestCustomRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestCustomRegistry:

    def test_register_custom_group_adds_entry(self):
        custom = register_custom_group(
            "beta_lactam",
            FGDefinition(
                name="Beta-Lactam",
                smarts="[C;R][NX3;R][CX3;R](=O)",
                category="nitrogen",
                description="Four-membered cyclic amide (beta-lactam ring).",
            ),
        )
        assert "beta_lactam" in custom

    def test_register_custom_group_does_not_mutate_global(self):
        before = len(FUNCTIONAL_GROUP_REGISTRY)
        register_custom_group(
            "test_mutation_guard",
            FGDefinition(
                name="Mutation Guard Test",
                smarts="[CH4]",
                category="test",
                description="Should not appear in global registry.",
            ),
        )
        assert len(FUNCTIONAL_GROUP_REGISTRY) == before

    def test_custom_detector_detects_new_pattern(self):
        # Methane detection as trivial custom pattern
        custom = register_custom_group(
            "methane_test",
            FGDefinition(
                name="Methane (test)", smarts="[CH4]",
                category="test", description="Detects methane molecule.",
            ),
        )
        d = FunctionalGroupDetector(registry=custom)
        r = d.detect(Chem.MolFromSmiles("C"))
        assert r.has("methane_test")

    def test_custom_detector_does_not_see_removed_key(self):
        """A registry without 'aromatic_ring' must not detect it."""
        custom = {k: v for k, v in FUNCTIONAL_GROUP_REGISTRY.items()
                  if k != "aromatic_ring"}
        d = FunctionalGroupDetector(registry=custom)
        r = d.detect(mol(BENZENE))
        assert not r.has("aromatic_ring")

    def test_overwrite_existing_key_warns_and_replaces(self, caplog):
        with caplog.at_level(logging.WARNING, logger="spectra.functional_group_detector"):
            custom = register_custom_group(
                "alcohol",
                FGDefinition(
                    name="Alcohol (overwritten)",
                    smarts="[OX2H1]",
                    category="oxygen",
                    description="Overwritten alcohol pattern.",
                ),
            )
        assert "alcohol" in custom
        assert any("overwrite" in rec.message.lower() or "already exists" in rec.message.lower()
                   for rec in caplog.records)

    def test_module_level_detect_function(self):
        r = detect_functional_groups(ASPIRIN)
        assert r.has("ester") and r.has("carboxylic_acid")

    def test_module_level_detect_accepts_mol_object(self):
        r = detect_functional_groups(mol(BENZENE))
        assert r.has("aromatic_ring")


# ═══════════════════════════════════════════════════════════════════════════════
# TestEdgeCases
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:

    def test_none_mol_raises_valueerror(self, detector):
        with pytest.raises(ValueError, match="None molecule"):
            detector.detect(None)

    def test_bad_smiles_raises_valueerror(self, detector):
        with pytest.raises(ValueError, match="could not parse"):
            detector.detect_from_smiles("NOTASMILES###")

    def test_empty_molecule_returns_empty_report(self, detector):
        """A mol with no atoms should return a report with zero matches."""
        empty_mol = Chem.RWMol()
        Chem.SanitizeMol(empty_mol)
        r = detector.detect(empty_mol.GetMol())
        assert r.total_groups == 0
        assert r.matches == []

    def test_chirality_flag_does_not_crash(self, detector):
        r = detector.detect(mol(IBUPROFEN), use_chirality=True)
        assert r.has("carboxylic_acid")

    def test_large_molecule_no_crash(self, detector):
        """Taxol (large, complex) must not crash the detector."""
        taxol = ("OC(=O)c1ccccc1)C(=O)O[C@@H]1C[C@]2(OC(C)=O)"
                 "C(=C([C@@H](OC(=O)c3ccccc3)C2(C)C)C(=O)O[C@H]1c4ccccc4)C")
        m = Chem.MolFromSmiles(taxol)
        if m is not None:
            r = detector.detect(m)
            assert r.total_groups >= 0  # just must not raise

    def test_detect_from_smiles_whitespace_raises(self, detector):
        """Whitespace-only SMILES should raise ValueError."""
        with pytest.raises(ValueError):
            detector.detect_from_smiles("   ")

    def test_inorganic_molecule_returns_empty(self, detector):
        """Pure water: no carbon-containing functional groups."""
        r = detector.detect_from_smiles("O")
        # Alcohol pattern requires a carbon — should not match water
        assert not r.has("alcohol")

    def test_match_count_correct_for_two_carboxylic_acids(self, detector):
        """Oxalic acid has 2 carboxylic acid groups."""
        r = detector.detect_from_smiles("OC(=O)C(=O)O")
        m = r.get("carboxylic_acid")
        assert m is not None and m.count == 2


# ═══════════════════════════════════════════════════════════════════════════════
# TestBatchConsistency
# ═══════════════════════════════════════════════════════════════════════════════

class TestBatchConsistency:

    def test_repeated_detect_same_results(self, detector):
        """Same molecule detected twice must return identical keys."""
        r1 = detector.detect(mol(ASPIRIN))
        r2 = detector.detect(mol(ASPIRIN))
        assert set(r1.keys) == set(r2.keys)

    def test_results_independent_across_molecules(self, detector):
        """Detection of one molecule must not affect the next."""
        r_aspirin = detector.detect(mol(ASPIRIN))
        r_benzene = detector.detect(mol(BENZENE))
        assert not r_benzene.has("carboxylic_acid")
        assert r_aspirin.has("carboxylic_acid")

    def test_all_reference_molecules_do_not_crash(self, detector):
        smiles_list = [
            ASPIRIN, CAFFEINE, BENZENE, ETHANOL, PHENOL, ACETIC_ACID,
            ETHYL_ACETATE, DIETHYL_ETHER, ACETALDEHYDE, ACETONE,
            METHYLAMINE, DIMETHYLAMINE, TRIETHYLAMINE, ACETAMIDE,
            ACETONITRILE, NITROBENZENE, CHLOROBENZENE, FLUOROBENZENE,
            BROMOBENZENE, IODOBENZENE, ETHANETHIOL, DIMETHYLSULFIDE,
            METHANESULFONAMIDE, STYRENE, PROPYNE, PARACETAMOL,
            IBUPROFEN, PENICILLIN_G, DIAZEPAM,
        ]
        for smi in smiles_list:
            r = detector.detect_from_smiles(smi)
            assert isinstance(r, FGReport)
            assert r.failed_patterns == []
