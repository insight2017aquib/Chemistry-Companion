import time

import pytest

from core import resolver
from rdkit import Chem


def test_resolve_smiles():
    res = resolver.resolve_molecule_input("CCO")
    assert res.success
    assert res.detected_type == "smiles"
    assert res.canonical_smiles == Chem.MolToSmiles(Chem.MolFromSmiles("CCO"), canonical=True)


def test_resolve_inchi():
    # Ethanol InChI
    inchi = "InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3"
    res = resolver.resolve_molecule_input(inchi)
    assert res.success
    assert res.detected_type == "inchi"
    assert res.canonical_smiles is not None


def test_resolve_name_monkeypatched(monkeypatch):
    # Monkeypatch the private PubChem resolver to avoid network dependency
    def fake_resolve(name, timeout=5):
        if name.lower() == "aspirin":
            return "CC(=O)Oc1ccccc1C(=O)O"
        return None

    monkeypatch.setattr(resolver, "_resolve_name_via_pubchem", fake_resolve)
    res = resolver.resolve_molecule_input("Aspirin")
    assert res.success
    assert res.detected_type == "name"
    assert "C(=O)O" in res.canonical_smiles


def test_resolve_name_to_smiles_pubchem_success(monkeypatch):
    monkeypatch.setattr(resolver, "_resolve_name_via_pubchem", lambda name, timeout=5: "CCO")
    monkeypatch.setattr(resolver, "_resolve_name_via_pubchem_fuzzy", lambda name, timeout=5: None)
    monkeypatch.setattr(resolver, "_resolve_name_via_opsin", lambda name, timeout=5: None)
    monkeypatch.setattr(resolver, "_resolve_name_via_iupac2struct", lambda name, timeout=5: None)

    smi = resolver.resolve_name_to_smiles("ethanol")
    assert smi == Chem.MolToSmiles(Chem.MolFromSmiles("CCO"), canonical=True)


def test_resolve_name_to_smiles_opsin_success(monkeypatch):
    monkeypatch.setattr(resolver, "_resolve_name_via_pubchem", lambda name, timeout=5: None)
    monkeypatch.setattr(resolver, "_resolve_name_via_pubchem_fuzzy", lambda name, timeout=5: None)
    monkeypatch.setattr(resolver, "_resolve_name_via_opsin", lambda name, timeout=5: "CCO")
    monkeypatch.setattr(resolver, "_resolve_name_via_iupac2struct", lambda name, timeout=5: None)

    smi = resolver.resolve_name_to_smiles("ethanol")
    assert smi == Chem.MolToSmiles(Chem.MolFromSmiles("CCO"), canonical=True)


def test_resolve_name_to_smiles_iupac2struct_success(monkeypatch):
    monkeypatch.setattr(resolver, "_resolve_name_via_pubchem", lambda name, timeout=5: None)
    monkeypatch.setattr(resolver, "_resolve_name_via_pubchem_fuzzy", lambda name, timeout=5: None)
    monkeypatch.setattr(resolver, "_resolve_name_via_opsin", lambda name, timeout=5: None)
    monkeypatch.setattr(resolver, "_resolve_name_via_iupac2struct", lambda name, timeout=5: "CCO")

    smi = resolver.resolve_name_to_smiles("ethanol")
    assert smi == Chem.MolToSmiles(Chem.MolFromSmiles("CCO"), canonical=True)


def test_resolve_name_to_smiles_fails_when_all_methods_fail(monkeypatch):
    monkeypatch.setattr(resolver, "_resolve_name_via_pubchem", lambda name, timeout=5: None)
    monkeypatch.setattr(resolver, "_resolve_name_via_pubchem_fuzzy", lambda name, timeout=5: None)
    monkeypatch.setattr(resolver, "_resolve_name_via_opsin", lambda name, timeout=5: None)
    monkeypatch.setattr(resolver, "_resolve_name_via_iupac2struct", lambda name, timeout=5: None)

    with pytest.raises(ValueError, match="Could not resolve name"):
        resolver.resolve_name_to_smiles("invalid-molecule-name-xyz")


def test_resolve_molfile_via_openbabel():
    mol = Chem.MolFromSmiles("CCO")
    mol_block = Chem.MolToMolBlock(mol)
    res = resolver.resolve_molecule_input(mol_block)
    assert res.success
    assert res.detected_type == "openbabel"
    assert res.source.startswith("openbabel-")
    assert res.canonical_smiles == Chem.MolToSmiles(Chem.MolFromSmiles("CCO"), canonical=True)


def test_openbabel_resolution_is_cached(monkeypatch):
    resolver._resolve_via_openbabel.cache_clear()
    monkeypatch.setattr(resolver, "_guess_openbabel_format", lambda text: "mol")
    calls = []

    def fake_convert(text, input_format, output_format):
        calls.append((text, input_format, output_format))
        return "CCO"

    monkeypatch.setattr(resolver, "convert_format", fake_convert)
    result1 = resolver._resolve_via_openbabel("dummy mol content", timeout=5)
    result2 = resolver._resolve_via_openbabel("dummy mol content", timeout=5)

    assert result1 == (Chem.MolToSmiles(Chem.MolFromSmiles("CCO"), canonical=True), "mol")
    assert result2 == result1
    assert len(calls) == 1


def test_openbabel_timeout_raises(monkeypatch):
    resolver._resolve_via_openbabel.cache_clear()
    monkeypatch.setattr(resolver, "_guess_openbabel_format", lambda text: "mol")

    def slow_convert(text, input_format, output_format):
        time.sleep(0.2)
        return "CCO"

    monkeypatch.setattr(resolver, "convert_format", slow_convert)

    with pytest.raises(TimeoutError, match="Open Babel conversion timed out"):
        resolver._resolve_via_openbabel("dummy mol content", timeout=0.01)
