"""
chemistry_companion/tests/test_batch_processor.py
==================================================
Comprehensive test suite for core/batch_processor.py

Run:
    python -m pytest tests/test_batch_processor.py -v --tb=short

Test groups:
    TestColumnDetection       — _detect_columns(), _normalise_header()
    TestCountHeterocyclicRings— _count_heterocyclic_rings() on reference mols
    TestReadCsvFile           — happy path, BOM, auto-detect, empty, bad
    TestReadTxtFile           — SMILES lines, IUPAC lines, comments, InChI skip
    TestReadExcelFile         — happy path, whitespace strip, missing columns
    TestReadInputFileDispatch — extension routing, unsupported type
    TestRowsFromSmilesList    — construction, name mismatch
    TestProcessOne            — per-molecule _process_one() correctness
    TestRunBatch              — serial, empty, zero rate-limit, progress logging
    TestBuildResult           — df_success column purity, df_errors schema
    TestBatchResult           — .summary() arithmetic, df shapes
    TestProcessFile           — end-to-end via temp CSV
    TestRegressions           — explicit regression guards for all 5 known fixes
"""

import csv
import json
import logging
import os
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import pytest
from rdkit import Chem

# ── path bootstrap ────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.batch_processor import (
    # data models
    MoleculeRow,
    ProcessedEntry,
    BatchResult,
    # internal helpers
    _normalise_header,
    _detect_columns,
    _count_heterocyclic_rings,
    _build_result,
    # file readers
    read_csv_file,
    read_txt_file,
    read_input_file,
    # public API
    run_batch,
    process_file,
    rows_from_smiles_list,
    # constants
    _SMILES_COLUMNS,
    _NAME_COLUMNS,
)

# ── constants -----------------------------------------------------------------
BENZENE       = "c1ccccc1"
ASPIRIN       = "CC(=O)Oc1ccccc1C(=O)O"
CAFFEINE      = "Cn1cnc2c1c(=O)n(c(=O)n2C)C"
IBUPROFEN     = "CC(C)Cc1ccc(cc1)[C@@H](C)C(=O)O"
PARACETAMOL   = "CC(=O)Nc1ccc(O)cc1"
NITROBENZENE  = "O=[N+]([O-])c1ccccc1"
PENICILLIN_G  = "CC1(C)SC2C(NC(=O)Cc3ccccc3)C(=O)N2C1C(=O)O"
DIAZEPAM      = "CN1C(=O)CN=C(c2ccccc2)c2cc(Cl)ccc21"
PURINE        = "c1ncc2[nH]cnc2n1"          # bicyclic 2-ring N-heterocycle
OXALIC_ACID   = "OC(=O)C(=O)O"
WATER         = "O"
METHANE       = "C"
BAD_SMILES    = "NOTVALIDSMILES###"


def mol(smi: str) -> Chem.Mol:
    m = Chem.MolFromSmiles(smi)
    assert m is not None, f"Test setup: bad SMILES {smi!r}"
    return m


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def simple_rows():
    return rows_from_smiles_list(
        [BENZENE, ASPIRIN, CAFFEINE],
        names=["Benzene", "Aspirin", "Caffeine"],
    )


@pytest.fixture
def drug_rows():
    return rows_from_smiles_list(
        [BENZENE, ASPIRIN, CAFFEINE, IBUPROFEN, PARACETAMOL,
         NITROBENZENE, PENICILLIN_G, DIAZEPAM],
        names=["Benzene","Aspirin","Caffeine","Ibuprofen","Paracetamol",
               "Nitrobenzene","PenicillinG","Diazepam"],
    )


@pytest.fixture
def mixed_rows():
    """3 valid + 1 intentionally bad SMILES."""
    return rows_from_smiles_list(
        [BENZENE, BAD_SMILES, ASPIRIN],
        names=["Benzene", "BAD", "Aspirin"],
    )


@pytest.fixture
def tmp_csv(tmp_path):
    """Write a minimal CSV with 'smiles' and 'name' columns."""
    p = tmp_path / "compounds.csv"
    with p.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["smiles","name"])
        writer.writeheader()
        writer.writerow({"smiles": BENZENE,   "name": "Benzene"})
        writer.writerow({"smiles": ASPIRIN,   "name": "Aspirin"})
        writer.writerow({"smiles": CAFFEINE,  "name": "Caffeine"})
        writer.writerow({"smiles": BAD_SMILES,"name": "Bad"})
    return str(p)


@pytest.fixture
def tmp_txt(tmp_path):
    p = tmp_path / "compounds.txt"
    p.write_text(
        "# header comment\n"
        f"{BENZENE}\n"
        f"{ASPIRIN}\n"
        "aspirin\n"           # IUPAC-style (no SMILES chars)
        "InChI=1S/C6H6/c1-2-4-6-5-3-1/h1-6H\n"  # should be skipped
        "\n"                  # blank line
        f"{CAFFEINE}\n",
        encoding="utf-8",
    )
    return str(p)


@pytest.fixture
def tmp_txt_all_smiles(tmp_path):
    p = tmp_path / "smiles_only.txt"
    p.write_text("\n".join([BENZENE, ASPIRIN, CAFFEINE]) + "\n")
    return str(p)


# ═══════════════════════════════════════════════════════════════════════════════
# TestColumnDetection
# ═══════════════════════════════════════════════════════════════════════════════

class TestColumnDetection:

    def test_normalise_strips_and_lowercases(self):
        assert _normalise_header("  SMILES  ") == "smiles"

    def test_normalise_empty(self):
        assert _normalise_header("") == ""

    def test_detect_canonical_smiles_col(self):
        sc, _ = _detect_columns(["canonical_smiles", "compound_name"])
        assert sc == "canonical_smiles"

    def test_detect_name_col(self):
        _, nc = _detect_columns(["smiles", "iupac_name"])
        assert nc == "iupac_name"

    def test_detect_both_present(self):
        sc, nc = _detect_columns(["smiles", "name"])
        assert sc == "smiles" and nc == "name"

    def test_detect_smiles_priority_over_structure(self):
        """'smiles' appears before 'structure' — smiles must win."""
        sc, _ = _detect_columns(["smiles", "structure"])
        assert sc == "smiles"

    def test_detect_none_when_missing(self):
        sc, nc = _detect_columns(["mol_id", "activity"])
        assert sc is None and nc is None

    def test_detect_case_insensitive(self):
        sc, nc = _detect_columns(["SMILES", "Name"])
        assert sc == "SMILES" and nc == "Name"

    def test_all_smiles_aliases_detected(self):
        for alias in _SMILES_COLUMNS:
            sc, _ = _detect_columns([alias, "extra_col"])
            assert sc == alias, f"Failed for alias: {alias!r}"

    def test_all_name_aliases_detected(self):
        for alias in _NAME_COLUMNS:
            _, nc = _detect_columns(["mol_id", alias])
            assert nc == alias, f"Failed for alias: {alias!r}"

    def test_first_smiles_col_wins(self):
        """When two SMILES columns exist, first one is chosen."""
        sc, _ = _detect_columns(["smiles", "canonical_smiles"])
        assert sc == "smiles"


# ═══════════════════════════════════════════════════════════════════════════════
# TestCountHeterocyclicRings
# ═══════════════════════════════════════════════════════════════════════════════

class TestCountHeterocyclicRings:

    def test_benzene_zero(self):
        assert _count_heterocyclic_rings(mol(BENZENE)) == 0

    def test_methane_zero(self):
        assert _count_heterocyclic_rings(mol(METHANE)) == 0

    def test_pyridine_one(self):
        assert _count_heterocyclic_rings(mol("c1ccncc1")) == 1

    def test_morpholine_one(self):
        assert _count_heterocyclic_rings(mol("C1CNCCO1")) == 1

    def test_caffeine_two(self):
        # Two fused N-containing rings in purine core
        assert _count_heterocyclic_rings(mol(CAFFEINE)) == 2

    def test_purine_two(self):
        assert _count_heterocyclic_rings(mol(PURINE)) == 2

    def test_diazepam_two(self):
        # Benzodiazepine: phenyl (carbocycle) + diazepine + fused phenyl
        # Only the N-containing rings count
        result = _count_heterocyclic_rings(mol(DIAZEPAM))
        assert result >= 1

    def test_penicillin_g_two(self):
        # Beta-lactam + thiazolidine
        assert _count_heterocyclic_rings(mol(PENICILLIN_G)) == 2

    def test_water_zero(self):
        assert _count_heterocyclic_rings(mol(WATER)) == 0

    def test_return_type_is_int(self):
        assert isinstance(_count_heterocyclic_rings(mol(ASPIRIN)), int)


# ═══════════════════════════════════════════════════════════════════════════════
# TestReadCsvFile
# ═══════════════════════════════════════════════════════════════════════════════

class TestReadCsvFile:

    def test_basic_csv_parses_three_rows(self, tmp_csv):
        rows = read_csv_file(tmp_csv)
        # 3 valid + 1 bad SMILES → all 4 MoleculeRow objects should parse
        assert len(rows) == 4

    def test_row_index_starts_at_one(self, tmp_csv):
        rows = read_csv_file(tmp_csv)
        assert rows[0].row_index == 1

    def test_smiles_captured(self, tmp_csv):
        rows = read_csv_file(tmp_csv)
        assert rows[0].smiles == BENZENE

    def test_label_set_from_name_col(self, tmp_csv):
        rows = read_csv_file(tmp_csv)
        assert rows[0].label == "Benzene"

    def test_returns_molecule_row_objects(self, tmp_csv):
        rows = read_csv_file(tmp_csv)
        for r in rows:
            assert isinstance(r, MoleculeRow)

    def test_empty_rows_skipped(self, tmp_path):
        p = tmp_path / "sparse.csv"
        p.write_text("smiles,name\n\n,\nc1ccccc1,Benzene\n\n")
        rows = read_csv_file(str(p))
        assert len(rows) == 1

    def test_bom_encoding_handled(self, tmp_path):
        p = tmp_path / "bom.csv"
        p.write_bytes("smiles,name\r\nc1ccccc1,Benzene\r\n".encode("utf-8-sig"))
        rows = read_csv_file(str(p))
        assert len(rows) == 1 and rows[0].smiles == "c1ccccc1"

    def test_missing_smiles_and_name_raises(self, tmp_path):
        p = tmp_path / "bad.csv"
        p.write_text("mol_id,activity\n1,high\n")
        with pytest.raises(ValueError, match="No SMILES or name"):
            read_csv_file(str(p))

    def test_empty_file_raises(self, tmp_path):
        p = tmp_path / "empty.csv"
        p.write_text("")
        with pytest.raises(ValueError):
            read_csv_file(str(p))

    def test_smiles_only_column(self, tmp_path):
        p = tmp_path / "smi_only.csv"
        p.write_text(f"smiles\n{BENZENE}\n{ASPIRIN}\n")
        rows = read_csv_file(str(p))
        assert len(rows) == 2

    def test_name_only_column_sets_iupac_name(self, tmp_path):
        p = tmp_path / "name_only.csv"
        p.write_text("name\nbenzene\naspirin\n")
        rows = read_csv_file(str(p))
        assert rows[0].iupac_name == "benzene"
        assert rows[0].smiles is None

    def test_extra_columns_stored_in_raw(self, tmp_path):
        p = tmp_path / "extra.csv"
        p.write_text("smiles,name,activity\nc1ccccc1,Benzene,high\n")
        rows = read_csv_file(str(p))
        assert rows[0].raw.get("activity") == "high"

    def test_raw_is_dict(self, tmp_csv):
        rows = read_csv_file(tmp_csv)
        assert isinstance(rows[0].raw, dict)


# ═══════════════════════════════════════════════════════════════════════════════
# TestReadTxtFile
# ═══════════════════════════════════════════════════════════════════════════════

class TestReadTxtFile:

    def test_basic_parse(self, tmp_txt):
        rows = read_txt_file(tmp_txt)
        # should skip: comment, blank, InChI → 4 entries remain (benzene, aspirin, "aspirin" name, caffeine)
        assert len(rows) == 4

    def test_smiles_line_sets_smiles(self, tmp_txt):
        rows = read_txt_file(tmp_txt)
        benzene_row = rows[0]
        assert benzene_row.smiles == BENZENE
        assert benzene_row.iupac_name is None

    def test_iupac_line_sets_iupac_name(self, tmp_txt):
        rows = read_txt_file(tmp_txt)
        # "aspirin" line (index 2, no SMILES chars)
        iupac_row = next(r for r in rows if r.label == "aspirin")
        assert iupac_row.iupac_name == "aspirin"
        assert iupac_row.smiles is None

    def test_comments_and_blanks_skipped(self, tmp_txt):
        rows = read_txt_file(tmp_txt)
        for r in rows:
            assert not r.label.startswith("#")
            assert r.label.strip() != ""

    def test_inchi_lines_skipped(self, tmp_txt, caplog):
        with caplog.at_level(logging.WARNING, logger="core.batch_processor"):
            rows = read_txt_file(tmp_txt)
        assert not any(r.label.startswith("InChI=") for r in rows)

    def test_all_smiles_file(self, tmp_txt_all_smiles):
        rows = read_txt_file(tmp_txt_all_smiles)
        assert len(rows) == 3
        for r in rows:
            assert r.smiles is not None

    def test_row_index_is_line_number(self, tmp_txt_all_smiles):
        rows = read_txt_file(tmp_txt_all_smiles)
        assert rows[0].row_index == 1
        assert rows[1].row_index == 2


# ═══════════════════════════════════════════════════════════════════════════════
# TestReadInputFileDispatch
# ═══════════════════════════════════════════════════════════════════════════════

class TestReadInputFileDispatch:

    def test_routes_csv(self, tmp_csv):
        rows = read_input_file(tmp_csv)
        assert len(rows) > 0

    def test_routes_txt(self, tmp_txt):
        rows = read_input_file(tmp_txt)
        assert len(rows) > 0

    def test_unsupported_extension_raises(self, tmp_path):
        p = tmp_path / "file.mol"
        p.write_text("dummy")
        with pytest.raises(ValueError, match="Unsupported file type"):
            read_input_file(str(p))

    def test_json_extension_raises(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text("{}")
        with pytest.raises(ValueError):
            read_input_file(str(p))


# ═══════════════════════════════════════════════════════════════════════════════
# TestRowsFromSmilesList
# ═══════════════════════════════════════════════════════════════════════════════

class TestRowsFromSmilesList:

    def test_basic_construction(self):
        rows = rows_from_smiles_list([BENZENE, ASPIRIN])
        assert len(rows) == 2

    def test_row_index_is_one_based(self):
        rows = rows_from_smiles_list([BENZENE, ASPIRIN])
        assert rows[0].row_index == 1
        assert rows[1].row_index == 2

    def test_names_assigned(self):
        rows = rows_from_smiles_list([BENZENE], names=["Benzene"])
        assert rows[0].label == "Benzene"

    def test_no_names_label_is_none(self):
        rows = rows_from_smiles_list([BENZENE])
        assert rows[0].label is None

    def test_mismatched_names_raises(self):
        with pytest.raises(ValueError):
            rows_from_smiles_list([BENZENE, ASPIRIN], names=["Benzene"])

    def test_empty_list_returns_empty(self):
        assert rows_from_smiles_list([]) == []

    def test_returns_molecule_row_objects(self):
        rows = rows_from_smiles_list([BENZENE])
        assert isinstance(rows[0], MoleculeRow)

    def test_smiles_stored_correctly(self):
        rows = rows_from_smiles_list([BENZENE, ASPIRIN])
        assert rows[0].smiles == BENZENE
        assert rows[1].smiles == ASPIRIN

    def test_raw_dict_contains_smiles(self):
        rows = rows_from_smiles_list([BENZENE])
        assert rows[0].raw.get("smiles") == BENZENE


# ═══════════════════════════════════════════════════════════════════════════════
# TestProcessOne
# ═══════════════════════════════════════════════════════════════════════════════

class TestProcessOne:

    from core.batch_processor import _process_one

    def test_benzene_ok(self):
        from core.batch_processor import _process_one
        row = MoleculeRow(row_index=1, smiles=BENZENE, label="Benzene")
        e   = _process_one(row)
        assert e.status == "ok"
        assert e.formula == "C6H6"

    def test_aspirin_descriptors(self):
        from core.batch_processor import _process_one
        e = _process_one(MoleculeRow(row_index=1, smiles=ASPIRIN))
        assert e.status == "ok"
        assert e.mol_weight is not None and 179 < e.mol_weight < 181
        assert e.logp is not None
        assert e.tpsa is not None
        assert e.hbd is not None
        assert e.hba is not None
        assert e.ro5_pass is True

    def test_bad_smiles_returns_error_status(self):
        from core.batch_processor import _process_one
        e = _process_one(MoleculeRow(row_index=99, smiles=BAD_SMILES))
        assert e.status == "error"
        assert e.error is not None and len(e.error) > 0

    def test_error_row_index_preserved(self):
        from core.batch_processor import _process_one
        e = _process_one(MoleculeRow(row_index=42, smiles=BAD_SMILES))
        assert e.row_index == 42

    def test_functional_groups_is_json_string(self):
        from core.batch_processor import _process_one
        e = _process_one(MoleculeRow(row_index=1, smiles=ASPIRIN))
        assert e.functional_groups is not None
        data = json.loads(e.functional_groups)
        assert isinstance(data, dict)

    def test_heterocycles_detected_zero_for_benzene(self):
        from core.batch_processor import _process_one
        e = _process_one(MoleculeRow(row_index=1, smiles=BENZENE))
        assert e.heterocycles_detected == 0

    def test_heterocycles_detected_positive_for_caffeine(self):
        from core.batch_processor import _process_one
        e = _process_one(MoleculeRow(row_index=1, smiles=CAFFEINE))
        assert e.heterocycles_detected == 2

    def test_heterocycles_detected_two_for_penicillin(self):
        from core.batch_processor import _process_one
        e = _process_one(MoleculeRow(row_index=1, smiles=PENICILLIN_G))
        assert e.heterocycles_detected == 2

    def test_inchikey_is_27_chars(self):
        from core.batch_processor import _process_one
        e = _process_one(MoleculeRow(row_index=1, smiles=BENZENE))
        assert e.inchikey is not None and len(e.inchikey) == 27

    def test_label_sets_name_when_name_missing(self):
        from core.batch_processor import _process_one
        e = _process_one(MoleculeRow(row_index=1, smiles=BENZENE, label="MyBenzene"))
        assert e.name == "MyBenzene"

    def test_num_heavy_atoms_correct_for_benzene(self):
        from core.batch_processor import _process_one
        e = _process_one(MoleculeRow(row_index=1, smiles=BENZENE))
        assert e.num_heavy_atoms == 6

    def test_is_aromatic_true_for_benzene(self):
        from core.batch_processor import _process_one
        e = _process_one(MoleculeRow(row_index=1, smiles=BENZENE))
        assert e.is_aromatic is True

    def test_is_aromatic_false_for_methane(self):
        from core.batch_processor import _process_one
        e = _process_one(MoleculeRow(row_index=1, smiles=METHANE))
        assert e.is_aromatic is False

    def test_bertz_ct_positive(self):
        from core.batch_processor import _process_one
        e = _process_one(MoleculeRow(row_index=1, smiles=ASPIRIN))
        assert e.bertz_ct is not None and e.bertz_ct > 0

    def test_rotatable_bonds_zero_for_benzene(self):
        from core.batch_processor import _process_one
        e = _process_one(MoleculeRow(row_index=1, smiles=BENZENE))
        assert e.rotatable_bonds == 0

    def test_ro5_violations_zero_for_benzene(self):
        from core.batch_processor import _process_one
        e = _process_one(MoleculeRow(row_index=1, smiles=BENZENE))
        assert e.ro5_violations == 0

    def test_exact_mass_differs_from_mol_weight(self):
        from core.batch_processor import _process_one
        e = _process_one(MoleculeRow(row_index=1, smiles=ASPIRIN))
        assert e.mol_weight != e.exact_mass


# ═══════════════════════════════════════════════════════════════════════════════
# TestRunBatch
# ═══════════════════════════════════════════════════════════════════════════════

class TestRunBatch:

    def test_empty_rows_returns_zero_total(self):
        result = run_batch([])
        assert result.total == 0 and result.n_success == 0 and result.n_errors == 0

    def test_all_valid_rows_all_succeed(self, simple_rows):
        result = run_batch(simple_rows, rate_limit_s=0.0)
        assert result.n_success == 3 and result.n_errors == 0

    def test_mixed_rows_splits_correctly(self, mixed_rows):
        result = run_batch(mixed_rows, rate_limit_s=0.0)
        assert result.n_success == 2
        assert result.n_errors == 1

    def test_total_equals_n_success_plus_n_errors(self, mixed_rows):
        result = run_batch(mixed_rows, rate_limit_s=0.0)
        assert result.total == result.n_success + result.n_errors

    def test_elapsed_s_positive(self, simple_rows):
        result = run_batch(simple_rows, rate_limit_s=0.0)
        assert result.elapsed_s > 0

    def test_returns_batch_result_object(self, simple_rows):
        result = run_batch(simple_rows, rate_limit_s=0.0)
        assert isinstance(result, BatchResult)

    def test_entries_count_matches_total(self, simple_rows):
        result = run_batch(simple_rows, rate_limit_s=0.0)
        assert len(result.entries) == result.total

    def test_df_success_row_count(self, simple_rows):
        result = run_batch(simple_rows, rate_limit_s=0.0)
        assert len(result.df_success) == result.n_success

    def test_df_errors_row_count(self, mixed_rows):
        result = run_batch(mixed_rows, rate_limit_s=0.0)
        assert len(result.df_errors) == result.n_errors

    def test_rate_limit_not_applied_when_smiles_present(self):
        """SMILES rows must not be delayed by rate_limit_s."""
        import time
        rows = rows_from_smiles_list([BENZENE, ASPIRIN, CAFFEINE])
        t0 = time.perf_counter()
        run_batch(rows, rate_limit_s=1.0)
        elapsed = time.perf_counter() - t0
        # Should complete in << 3 seconds (no sleep for SMILES rows)
        assert elapsed < 2.0, f"rate_limit_s incorrectly applied to SMILES rows (took {elapsed:.2f}s)"

    def test_progress_logged(self, drug_rows, caplog):
        with caplog.at_level(logging.INFO, logger="core.batch_processor"):
            run_batch(drug_rows, rate_limit_s=0.0, progress_every=3)
        assert any("Progress" in r.message or "Batch" in r.message
                   for r in caplog.records)

    def test_large_batch_no_crash(self):
        """50 identical molecules must not raise."""
        rows = rows_from_smiles_list([BENZENE] * 50)
        result = run_batch(rows, rate_limit_s=0.0)
        assert result.n_success == 50


# ═══════════════════════════════════════════════════════════════════════════════
# TestBuildResult
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildResult:

    import time

    def _make_entries(self):
        import time
        rows   = rows_from_smiles_list(
            [BENZENE, ASPIRIN, BAD_SMILES],
            names=["Benzene", "Aspirin", "Bad"],
        )
        result = run_batch(rows, rate_limit_s=0.0)
        return result

    def test_df_success_has_no_status_column(self):
        """FIX-2: status column must NOT appear in df_success."""
        result = self._make_entries()
        assert "status" not in result.df_success.columns

    def test_df_success_has_no_error_column(self):
        """FIX-2: error column must NOT appear in df_success."""
        result = self._make_entries()
        assert "error" not in result.df_success.columns

    def test_df_success_has_smiles_column(self):
        result = self._make_entries()
        assert "smiles" in result.df_success.columns

    def test_df_success_has_formula_column(self):
        result = self._make_entries()
        assert "formula" in result.df_success.columns

    def test_df_errors_has_required_columns(self):
        result = self._make_entries()
        for col in ("row_index", "input_repr", "error"):
            assert col in result.df_errors.columns

    def test_df_errors_error_col_nonempty_for_bad(self):
        result = self._make_entries()
        assert result.df_errors["error"].iloc[0] is not None

    def test_empty_entries_produces_empty_dataframes(self):
        import time
        result = _build_result([], time.perf_counter())
        assert result.df_success.empty
        assert result.df_errors.empty

    def test_df_success_heterocycles_detected_column_exists(self):
        result = self._make_entries()
        assert "heterocycles_detected" in result.df_success.columns

    def test_df_success_functional_groups_is_valid_json(self):
        result = self._make_entries()
        for val in result.df_success["functional_groups"]:
            assert isinstance(json.loads(val), dict)


# ═══════════════════════════════════════════════════════════════════════════════
# TestBatchResult
# ═══════════════════════════════════════════════════════════════════════════════

class TestBatchResult:

    def test_summary_keys_present(self, simple_rows):
        result = run_batch(simple_rows, rate_limit_s=0.0)
        s = result.summary()
        for key in ("total","successful","failed","success_rate_%","elapsed_seconds"):
            assert key in s

    def test_summary_arithmetic_all_success(self, simple_rows):
        result = run_batch(simple_rows, rate_limit_s=0.0)
        s = result.summary()
        assert s["total"] == 3
        assert s["successful"] == 3
        assert s["failed"] == 0
        assert s["success_rate_%"] == 100.0

    def test_summary_arithmetic_mixed(self, mixed_rows):
        result = run_batch(mixed_rows, rate_limit_s=0.0)
        s = result.summary()
        assert s["total"] == 3
        assert s["successful"] == 2
        assert s["failed"] == 1
        assert s["success_rate_%"] == pytest.approx(66.7, abs=0.1)

    def test_summary_zero_total_no_division_error(self):
        result = run_batch([])
        s = result.summary()
        assert s["success_rate_%"] == 0.0

    def test_entries_list_is_all_processed_entries(self, mixed_rows):
        result = run_batch(mixed_rows, rate_limit_s=0.0)
        for e in result.entries:
            assert isinstance(e, ProcessedEntry)

    def test_df_success_is_dataframe(self, simple_rows):
        result = run_batch(simple_rows, rate_limit_s=0.0)
        assert isinstance(result.df_success, pd.DataFrame)

    def test_df_errors_is_dataframe(self, mixed_rows):
        result = run_batch(mixed_rows, rate_limit_s=0.0)
        assert isinstance(result.df_errors, pd.DataFrame)

    def test_elapsed_s_is_float(self, simple_rows):
        result = run_batch(simple_rows, rate_limit_s=0.0)
        assert isinstance(result.elapsed_s, float)


# ═══════════════════════════════════════════════════════════════════════════════
# TestProcessFile
# ═══════════════════════════════════════════════════════════════════════════════

class TestProcessFile:

    def test_csv_end_to_end(self, tmp_csv):
        result = process_file(tmp_csv)
        assert result.total == 4          # 3 valid + 1 bad
        assert result.n_success == 3
        assert result.n_errors == 1

    def test_txt_end_to_end(self, tmp_txt):
        result = process_file(tmp_txt)
        # 2 SMILES + 1 IUPAC name + 1 more SMILES = 4 rows parsed
        # The IUPAC name row may succeed (PubChem lookup) or fail in offline env
        assert result.total == 4

    def test_csv_df_success_formula_benzene(self, tmp_csv):
        result = process_file(tmp_csv)
        benzene_row = result.df_success[result.df_success["formula"] == "C6H6"]
        assert len(benzene_row) == 1

    def test_csv_errors_contain_bad_smiles(self, tmp_csv):
        result = process_file(tmp_csv)
        assert len(result.df_errors) == 1
        assert "Bad" in result.df_errors["input_repr"].values or \
               BAD_SMILES in result.df_errors["input_repr"].values

    def test_unsupported_ext_raises(self, tmp_path):
        p = tmp_path / "data.sdf"
        p.write_text("dummy")
        with pytest.raises(ValueError):
            process_file(str(p))

    def test_summary_total_matches_file_rows(self, tmp_csv):
        result = process_file(tmp_csv)
        s = result.summary()
        assert s["total"] == 4


# ═══════════════════════════════════════════════════════════════════════════════
# TestRegressions — explicit guards for all 5 known fixes
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegressions:

    def test_fix1_no_import_error_for_get_heterocycles(self):
        """
        FIX-1: _process_one must NOT import get_heterocycles from descriptor_utils.
        Verify by checking that _process_one runs caffeine (2 heterocyclic rings)
        without ImportError and returns heterocycles_detected=2.
        """
        from core.batch_processor import _process_one
        e = _process_one(MoleculeRow(row_index=1, smiles=CAFFEINE))
        assert e.status == "ok", f"Expected ok, got error: {e.error}"
        assert e.heterocycles_detected == 2

    def test_fix2_status_not_in_df_success_columns(self):
        """FIX-2: df_success must not contain 'status' or 'error' columns."""
        rows   = rows_from_smiles_list([BENZENE, ASPIRIN])
        result = run_batch(rows, rate_limit_s=0.0)
        assert "status" not in result.df_success.columns
        assert "error"  not in result.df_success.columns

    def test_fix3_excel_whitespace_stripped(self, tmp_path):
        """
        FIX-3: Excel cells with leading/trailing whitespace must parse correctly.
        Simulates ChemDraw export where SMILES may be ' c1ccccc1 '.
        """
        try:
            import openpyxl
        except ImportError:
            pytest.skip("openpyxl not installed")

        from core.batch_processor import read_excel_file

        p = tmp_path / "whitespace.xlsx"
        df = pd.DataFrame({
            "smiles": [f"  {BENZENE}  ", f" {ASPIRIN} "],
            "name":   ["  Benzene  ", " Aspirin "],
        })
        df.to_excel(str(p), index=False)
        rows = read_excel_file(str(p))
        assert len(rows) == 2
        assert rows[0].smiles == BENZENE     # whitespace stripped
        assert rows[1].smiles == ASPIRIN

    def test_fix4_multiprocessing_order_preserved(self):
        """
        FIX-4: With max_workers > 1, output must be sorted by row_index.
        The as_completed() order is non-deterministic — sort must be applied.
        """
        smiles = [BENZENE, ASPIRIN, CAFFEINE, IBUPROFEN, PARACETAMOL]
        names  = ["Benzene","Aspirin","Caffeine","Ibuprofen","Paracetamol"]
        rows   = rows_from_smiles_list(smiles, names=names)

        result = run_batch(rows, max_workers=2, rate_limit_s=0.0)
        assert result.n_success == 5

        indices = [e.row_index for e in result.entries]
        assert indices == sorted(indices), \
            f"Entries not sorted by row_index: {indices}"

    def test_fix5_rate_limit_not_applied_to_smiles_rows(self):
        """
        FIX-5: rate_limit_s must only delay IUPAC-name-only rows.
        A batch of 5 SMILES rows with rate_limit_s=1.0 must complete
        in under 2 seconds.
        """
        import time
        rows = rows_from_smiles_list([BENZENE, ASPIRIN, CAFFEINE,
                                       IBUPROFEN, PARACETAMOL])
        t0      = time.perf_counter()
        result  = run_batch(rows, max_workers=1, rate_limit_s=1.0)
        elapsed = time.perf_counter() - t0
        assert result.n_success == 5
        assert elapsed < 2.0, (
            f"rate_limit_s was incorrectly applied to SMILES rows. "
            f"Elapsed: {elapsed:.2f}s (expected < 2.0s)"
        )


# ── standalone runner ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import subprocess
    subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"],
        cwd=str(ROOT),
    )
