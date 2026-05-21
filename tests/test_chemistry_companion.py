"""
tests/test_chemistry_companion.py
==================================
Pytest suite for chemistry_companion.py
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import chemistry_companion as cc
from core.molecule_utils import MoleculeRecord, load_molecule
from core.descriptor_utils import DescriptorRecord, compute_descriptors, summarise_descriptors
from reports.export_utils import export_batch

# ====================== CORRECT IMPORTS ======================
from spectra.ir_predictor import predict_ir
from spectra.proton_nmr import predict_proton_nmr
from spectra.carbon_nmr import predict_carbon_nmr


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def benzene_rec() -> MoleculeRecord:
    m = load_molecule(smiles="c1ccccc1")
    m.name = "Benzene"
    return m


@pytest.fixture(scope="session")
def aspirin_rec() -> MoleculeRecord:
    m = load_molecule(smiles="CC(=O)Oc1ccccc1C(=O)O")
    m.name = "Aspirin"
    return m


@pytest.fixture(scope="session")
def caffeine_rec() -> MoleculeRecord:
    m = load_molecule(smiles="Cn1cnc2c1c(=O)n(c(=O)n2C)C")
    m.name = "Caffeine"
    return m


@pytest.fixture(scope="session")
def ibuprofen_rec() -> MoleculeRecord:
    m = load_molecule(smiles="CC(C)Cc1ccc(cc1)C(C)C(=O)O")
    m.name = "Ibuprofen"
    return m


@pytest.fixture(scope="session")
def toluene_rec() -> MoleculeRecord:
    return load_molecule(smiles="Cc1ccccc1")


@pytest.fixture(scope="session")
def acetic_acid_rec() -> MoleculeRecord:
    return load_molecule(smiles="CC(=O)O")


@pytest.fixture(scope="session")
def aniline_rec() -> MoleculeRecord:
    return load_molecule(smiles="Nc1ccccc1")


@pytest.fixture(scope="session")
def ethanol_rec() -> MoleculeRecord:
    return load_molecule(smiles="CCO")


@pytest.fixture(scope="session")
def acetamide_rec() -> MoleculeRecord:
    return load_molecule(smiles="CC(=O)N")


@pytest.fixture(scope="session")
def nitrobenzene_rec() -> MoleculeRecord:
    return load_molecule(smiles="O=[N+]([O-])c1ccccc1")


@pytest.fixture
def tmp_out(tmp_path: Path) -> Path:
    d = tmp_path / "output"
    d.mkdir()
    return d


@pytest.fixture
def standard_batch_csv(tmp_path: Path) -> Path:
    p = tmp_path / "batch.csv"
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["name", "smiles"])
        w.writerow(["Benzene", "c1ccccc1"])
        w.writerow(["Aspirin", "CC(=O)Oc1ccccc1C(=O)O"])
        w.writerow(["Empty", ""])
        w.writerow(["BadSMILES", "NOT_VALID!!!"])
    return p


@pytest.fixture
def minimal_batch_csv(tmp_path: Path) -> Path:
    p = tmp_path / "minimal.csv"
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["smiles"])
        w.writerow(["c1ccccc1"])
        w.writerow(["CC(=O)O"])
    return p


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _args(argv: list[str]) -> argparse.Namespace:
    return cc.build_parser().parse_args(argv)


# ---------------------------------------------------------------------------
# Safe-name and banner
# ---------------------------------------------------------------------------

class TestSafeName:
    @pytest.mark.parametrize(
        "inp, expected",
        [
            ("Methyl Ester", "Methyl_Ester"),
            ("2/3-compound", "2_3-compound"),
            ("a\\b", "a_b"),
            ("a:b*c?", "a_b_c"),
            ('a"b', "a_b"),
            ("a<b>c", "a_b_c"),
            ("a|b", "a_b"),
            ("Caffeine", "Caffeine"),
            ("  .name.", "name"),
            ("Compound 1", "Compound_1"),
            ("penicillin-G", "penicillin-G"),
            ("(R)-ibuprofen", "(R)-ibuprofen"),
        ],
    )
    def test_basic(self, inp, expected):
        assert cc._safe_name(inp) == expected

    def test_empty_string_returns_string(self):
        assert isinstance(cc._safe_name(""), str)


class TestBanner:
    def test_contains_name(self):
        assert "Chemistry Companion" in cc._banner()

    def test_contains_version(self):
        assert cc.VERSION in cc._banner()

    def test_contains_rdkit(self):
        assert "RDKit" in cc._banner()

    def test_starts_with_real_newline(self):
        assert cc._banner().startswith("\n")

    def test_no_literal_escaped_newline(self):
        assert "\\n" not in cc._banner()


# ---------------------------------------------------------------------------
# Resolve output dir and load helpers
# ---------------------------------------------------------------------------

class TestResolveOutputDir:
    def test_cli_dir_wins(self):
        assert cc._resolve_output_dir("/tmp/custom") == "/tmp/custom"

    def test_settings_used_when_cli_default(self):
        mock_settings = MagicMock()
        mock_settings.directories.output_dir = Path("/settings/path")
        assert cc._resolve_output_dir("output", settings=mock_settings) == "/settings/path"

    def test_settings_object_without_attr_falls_back(self):
        mock_settings = object()
        assert cc._resolve_output_dir("output", settings=mock_settings) == "output"


class TestLoadMolHelper:
    def test_load_smiles(self):
        ns = argparse.Namespace(smiles="c1ccccc1", inchi=None, file=None, iupac=None, name=None)
        mol = cc._load_mol(ns)
        assert mol.formula == "C6H6"

    def test_name_override(self):
        ns = argparse.Namespace(smiles="c1ccccc1", inchi=None, file=None, iupac=None, name="Benzene")
        mol = cc._load_mol(ns)
        assert mol.name == "Benzene"

    def test_no_input_raises(self):
        ns = argparse.Namespace(smiles=None, inchi=None, file=None, iupac=None, name=None)
        with pytest.raises(ValueError):
            cc._load_mol(ns)


# ---------------------------------------------------------------------------
# Molecule parsing and descriptors
# ---------------------------------------------------------------------------

class TestMoleculeUtils:
    def test_benzene_formula(self, benzene_rec):
        assert benzene_rec.formula == "C6H6"

    def test_aspirin_formula(self, aspirin_rec):
        assert aspirin_rec.formula == "C9H8O4"

    def test_caffeine_formula(self, caffeine_rec):
        assert caffeine_rec.formula == "C8H10N4O2"

    def test_ibuprofen_formula(self, ibuprofen_rec):
        assert ibuprofen_rec.formula == "C13H18O2"

    def test_benzene_exact_mass(self, benzene_rec):
        assert abs(benzene_rec.exact_mass - 78.047) < 0.01

    def test_aspirin_exact_mass(self, aspirin_rec):
        assert abs(aspirin_rec.exact_mass - 180.0423) < 0.001

    def test_caffeine_inchikey(self, caffeine_rec):
        assert caffeine_rec.inchikey == "RYYVLZVUVIJVGH-UHFFFAOYSA-N"

    def test_invalid_smiles_raises(self):
        with pytest.raises(ValueError, match="Invalid SMILES"):
            load_molecule(smiles="NOT_VALID!!!")

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_molecule(file_path=str(tmp_path / "ghost.mol"))

    def test_inchi_parsing(self, benzene_rec):
        m2 = load_molecule(inchi=benzene_rec.inchi)
        assert m2.formula == "C6H6"


class TestDescriptorValues:
    def test_descriptor_record_type(self, benzene_rec):
        d = compute_descriptors(benzene_rec.rdkit_mol, mw=benzene_rec.mol_weight)
        assert isinstance(d, DescriptorRecord)

    def test_benzene_tpsa_zero(self, benzene_rec):
        d = compute_descriptors(benzene_rec.rdkit_mol, mw=benzene_rec.mol_weight)
        assert d.tpsa == 0.0

    def test_benzene_ro5_pass(self, benzene_rec):
        d = compute_descriptors(benzene_rec.rdkit_mol, mw=benzene_rec.mol_weight)
        assert d.ro5_pass is True
        assert d.ro5_violations == 0

    def test_aspirin_logp(self, aspirin_rec):
        d = compute_descriptors(aspirin_rec.rdkit_mol, mw=aspirin_rec.mol_weight)
        assert abs(d.logp - 1.3101) < 0.05

    def test_aspirin_tpsa(self, aspirin_rec):
        d = compute_descriptors(aspirin_rec.rdkit_mol, mw=aspirin_rec.mol_weight)
        assert abs(d.tpsa - 63.6) < 1.0

    def test_aspirin_hbd_hba(self, aspirin_rec):
        d = compute_descriptors(aspirin_rec.rdkit_mol, mw=aspirin_rec.mol_weight)
        assert d.hbd == 1
        assert d.hba == 3

    def test_caffeine_logp_negative(self, caffeine_rec):
        d = compute_descriptors(caffeine_rec.rdkit_mol, mw=caffeine_rec.mol_weight)
        assert d.logp < 0

    def test_ibuprofen_logp_above_3(self, ibuprofen_rec):
        d = compute_descriptors(ibuprofen_rec.rdkit_mol, mw=ibuprofen_rec.mol_weight)
        assert d.logp > 3.0


class TestFunctionalGroupSMARTS:
    def test_aspirin_has_carboxylic_acid(self, aspirin_rec):
        d = compute_descriptors(aspirin_rec.rdkit_mol)
        assert d.has_carboxylic_acid is True

    def test_aspirin_has_aromatic_ring(self, aspirin_rec):
        d = compute_descriptors(aspirin_rec.rdkit_mol)
        assert d.has_aromatic_ring is True

    def test_ethanol_has_hydroxyl(self, ethanol_rec):
        d = compute_descriptors(ethanol_rec.rdkit_mol)
        assert d.has_hydroxyl is True

    def test_aniline_has_primary_amine(self, aniline_rec):
        d = compute_descriptors(aniline_rec.rdkit_mol)
        assert d.has_primary_amine is True

    def test_acetamide_has_amide(self, acetamide_rec):
        d = compute_descriptors(acetamide_rec.rdkit_mol)
        assert d.has_amide is True

    def test_nitrobenzene_has_nitro(self, nitrobenzene_rec):
        d = compute_descriptors(nitrobenzene_rec.rdkit_mol)
        assert d.has_nitro is True

    def test_fg_fields_are_bool(self, aspirin_rec):
        d = compute_descriptors(aspirin_rec.rdkit_mol)
        for key, value in vars(d).items():
            if key.startswith("has_"):
                assert isinstance(value, bool)


class TestSummariseDescriptors:
    def test_returns_string(self, benzene_rec):
        d = compute_descriptors(benzene_rec.rdkit_mol, mw=benzene_rec.mol_weight)
        assert isinstance(summarise_descriptors(d), str)

    def test_contains_core_fields(self, aspirin_rec):
        d = compute_descriptors(aspirin_rec.rdkit_mol, mw=aspirin_rec.mol_weight)
        s = summarise_descriptors(d)
        assert "LogP" in s and "TPSA" in s and "HBD" in s and "HBA" in s


# ---------------------------------------------------------------------------
# Pipelines
# ---------------------------------------------------------------------------

class TestRunAnalyse:
    def test_returns_tuple(self, tmp_out):
        result = cc.run_analyse(smiles="c1ccccc1", output_dir=str(tmp_out))
        assert isinstance(result, tuple) and len(result) == 2

    def test_returns_records(self, tmp_out):
        mol_rec, desc_rec = cc.run_analyse(smiles="c1ccccc1", output_dir=str(tmp_out))
        assert isinstance(mol_rec, MoleculeRecord)
        assert desc_rec is not None

    def test_save_image_creates_png(self, tmp_out):
        cc.run_analyse(smiles="c1ccccc1", name="Benzene", save_image=True, output_dir=str(tmp_out))
        pngs = list(tmp_out.glob("*.png"))
        assert len(pngs) == 1
        assert pngs[0].stat().st_size > 500

    def test_export_csv_json(self, tmp_out):
        cc.run_analyse(
            smiles="c1ccccc1",
            name="Benzene",
            export=["csv", "json"],
            output_dir=str(tmp_out),
        )
        assert len(list(tmp_out.glob("*.csv"))) == 1
        assert len(list(tmp_out.glob("*.json"))) == 1

    def test_no_input_raises(self, tmp_out):
        with pytest.raises(ValueError):
            cc.run_analyse(output_dir=str(tmp_out))

    def test_inchi_input(self, tmp_out):
        mol_rec, _ = cc.run_analyse(
            inchi="InChI=1S/C6H6/c1-2-4-6-5-3-1/h1-6H",
            output_dir=str(tmp_out),
        )
        assert mol_rec.formula == "C6H6"


class TestRunFuncgroups:
    def test_returns_dict(self, aspirin_rec):
        fg = cc.run_funcgroups(aspirin_rec)
        assert isinstance(fg, dict)
        assert fg["has_carboxylic_acid"] is True


class TestRunIR:
    def test_returns_dict(self, aspirin_rec):
        result = cc.run_ir(aspirin_rec)
        assert isinstance(result, dict)

    def test_aspirin_has_carbonyl_band(self, aspirin_rec):
        result = cc.run_ir(aspirin_rec)
        assert any("C=O" in k or "Carbonyl" in k for k in result.keys())

    def test_graceful_missing_module(self, aspirin_rec):
        with patch.dict(sys.modules, {"spectra.ir_predictor": None}):
            result = cc.run_ir(aspirin_rec)
        assert isinstance(result, dict)


class TestRunHNMR:
    def test_returns_dict(self, toluene_rec):
        result = cc.run_hnmr(toluene_rec)
        assert isinstance(result, dict)

    def test_toluene_has_aromatic_h(self, toluene_rec):
        result = cc.run_hnmr(toluene_rec)
        assert any("Aromatic" in k for k in result.keys())

    def test_toluene_has_aliphatic_methyl_label(self, toluene_rec):
        result = cc.run_hnmr(toluene_rec)
        assert any("CH3 aliphatic" in k or "Benzylic" in k for k in result.keys())


class TestRunCNMR:
    def test_returns_dict(self, acetic_acid_rec):
        result = cc.run_cnmr(acetic_acid_rec)
        assert isinstance(result, dict)

    def test_acetic_acid_carboxylic_shift(self, acetic_acid_rec):
        result = cc.run_cnmr(acetic_acid_rec)
        cooh = {k: v for k, v in result.items() if "Carboxylic" in k and isinstance(v, float)}
        assert len(cooh) >= 1
        shift = list(cooh.values())[0]
        assert 170.0 < shift < 185.0

    def test_toluene_has_aliphatic_methyl_label(self, toluene_rec):
        result = cc.run_cnmr(toluene_rec)
        assert any("CH3 aliphatic" in k or "Benzylic" in k for k in result.keys())


class TestRunBatch:
    def test_two_valid_rows_succeed(self, standard_batch_csv, tmp_out):
        results = cc.run_batch(str(standard_batch_csv), output_dir=str(tmp_out))
        assert len(results) == 2

    def test_bad_rows_do_not_abort(self, standard_batch_csv, tmp_out):
        results = cc.run_batch(str(standard_batch_csv), output_dir=str(tmp_out))
        names = [r[0].name for r in results]
        assert "Benzene" in names and "Aspirin" in names
        assert "BadSMILES" not in names

    def test_auto_label_without_name_column(self, minimal_batch_csv, tmp_out):
        results = cc.run_batch(str(minimal_batch_csv), output_dir=str(tmp_out))
        assert results[0][0].name == "compound_1"
        assert results[1][0].name == "compound_2"

    def test_missing_file_raises(self, tmp_out):
        with pytest.raises(FileNotFoundError):
            cc.run_batch(str(tmp_out / "ghost.csv"), output_dir=str(tmp_out))


# ---------------------------------------------------------------------------
# Parser and CLI handlers
# ---------------------------------------------------------------------------

class TestBuildParser:
    def test_returns_parser(self):
        assert isinstance(cc.build_parser(), argparse.ArgumentParser)

    def test_verbose_flag(self):
        args = _args(["--verbose", "version"])
        assert args.verbose is True

    def test_mutually_exclusive_inputs(self):
        with pytest.raises(SystemExit):
            _args([
                "analyse",
                "--smiles", "c1ccccc1",
                "--inchi", "InChI=1S/C6H6/c1-2-4-6-5-3-1/h1-6H",
            ])

    def test_help_root(self):
        with pytest.raises(SystemExit) as exc:
            cc.build_parser().parse_args(["--help"])
        assert exc.value.code == 0


class TestCmdAnalyse:
    def test_runs(self, tmp_out, capsys):
        args = _args(["analyse", "--smiles", "c1ccccc1", "--name", "Benzene", "--output-dir", str(tmp_out)])
        cc._cmd_analyse(args, settings=None)
        assert "C6H6" in capsys.readouterr().out

    def test_invalid_smiles_exit_1(self, tmp_out):
        args = _args(["analyse", "--smiles", "NOT_VALID!!!", "--output-dir", str(tmp_out)])
        with pytest.raises(SystemExit) as exc:
            cc._cmd_analyse(args, settings=None)
        assert exc.value.code == 1


class TestCmdBatch:
    def test_runs(self, standard_batch_csv, tmp_out, capsys):
        args = _args(["batch", "--file", str(standard_batch_csv), "--output-dir", str(tmp_out)])
        cc._cmd_batch(args, settings=None)
        assert "Batch finished" in capsys.readouterr().out


class TestCmdIR:
    def test_runs(self, capsys):
        args = _args(["ir", "--smiles", "CC(=O)Oc1ccccc1C(=O)O"])
        cc._cmd_ir(args, settings=None)
        assert "APPROXIMATE" in capsys.readouterr().out


class TestCmdHNMR:
    def test_runs(self, capsys):
        args = _args(["hnmr", "--smiles", "Cc1ccccc1"])
        cc._cmd_hnmr(args, settings=None)
        assert "ppm" in capsys.readouterr().out


class TestCmdCNMR:
    def test_runs(self, capsys):
        args = _args(["cnmr", "--smiles", "CC(=O)O"])
        cc._cmd_cnmr(args, settings=None)
        assert "ppm" in capsys.readouterr().out


class TestCmdFuncgroups:
    def test_runs(self, capsys):
        args = _args(["funcgroups", "--smiles", "CC(=O)Oc1ccccc1C(=O)O"])
        cc._cmd_funcgroups(args, settings=None)
        assert "Detected" in capsys.readouterr().out


class TestCmdImage:
    def test_creates_png(self, tmp_out):
        args = _args(["image", "--smiles", "c1ccccc1", "--name", "Benzene", "--output-dir", str(tmp_out)])
        cc._cmd_image(args, settings=None)
        assert len(list(tmp_out.glob("*.png"))) == 1


class TestCmdExport:
    def test_creates_csv_json(self, tmp_out):
        args = _args([
            "export", "--smiles", "c1ccccc1",
            "--formats", "csv", "json",
            "--output-dir", str(tmp_out),
        ])
        cc._cmd_export(args, settings=None)
        assert len(list(tmp_out.glob("*.csv"))) == 1
        assert len(list(tmp_out.glob("*.json"))) == 1


class TestCmdDemo:
    def test_creates_demo_outputs(self, tmp_out):
        args = _args(["demo", "--output-dir", str(tmp_out)])
        cc._cmd_demo(args, settings=None)
        assert len(list(tmp_out.glob("*.png"))) == 4


class TestCmdVersion:
    def test_outputs_environment_info(self, capsys):
        args = _args(["version"])
        cc._cmd_version(args, settings=None)
        out = capsys.readouterr().out
        assert "Python" in out and "Platform" in out and "Chemistry Companion" in out


class TestErrorPaths:
    def test_unexpected_exception_exits_2(self, tmp_out):
        args = _args(["analyse", "--smiles", "c1ccccc1", "--output-dir", str(tmp_out)])
        with patch("chemistry_companion.run_analyse", side_effect=RuntimeError("boom")):
            with pytest.raises(SystemExit) as exc:
                cc._cmd_analyse(args, settings=None)
        assert exc.value.code == 2


# ---------------------------------------------------------------------------
# Export utils and spectra standalone
# ---------------------------------------------------------------------------

class TestExportBatch:
    def test_csv_and_json_valid(self, benzene_rec, tmp_out):
        d = compute_descriptors(benzene_rec.rdkit_mol, mw=benzene_rec.mol_weight)
        paths = export_batch([(benzene_rec, d)], output_dir=str(tmp_out), base_name="Benzene", formats=["csv", "json"])
        with open(paths["csv"], newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        with open(paths["json"], encoding="utf-8") as fh:
            data = json.load(fh)
        assert rows[0]["formula"] == "C6H6"
        assert data[0]["formula"] == "C6H6"


class TestIRPredictor:
    def test_benzene_has_aromatic_bands(self, benzene_rec):
        result = predict_ir(benzene_rec.rdkit_mol)
        assert any("Aromatic" in k for k in result.keys())

    def test_acetic_acid_has_carboxylic_band(self, acetic_acid_rec):
        result = predict_ir(acetic_acid_rec.rdkit_mol)
        assert any("Carboxylic" in k for k in result.keys())


class TestProtonNMR:
    def test_benzene_aromatic_h(self, benzene_rec):
        result = predict_proton_nmr(benzene_rec.rdkit_mol)
        assert any("Aromatic" in k for k in result.keys())

    def test_benzene_aromatic_shift(self, benzene_rec):
        result = predict_proton_nmr(benzene_rec.rdkit_mol)
        aromatic = {k: v for k, v in result.items() if "Aromatic" in k}
        assert list(aromatic.values())[0] == pytest.approx(7.27, abs=0.15)


class TestCarbonNMR:
    def test_acetic_carboxylic_shift(self, acetic_acid_rec):
        result = predict_carbon_nmr(acetic_acid_rec.rdkit_mol)
        cooh = {k: v for k, v in result.items() if "Carboxylic" in k}
        assert list(cooh.values())[0] == pytest.approx(178.0, abs=3.0)

    def test_aspirin_multiple_environments(self, aspirin_rec):
        result = predict_carbon_nmr(aspirin_rec.rdkit_mol)
        assert len(result) >= 3