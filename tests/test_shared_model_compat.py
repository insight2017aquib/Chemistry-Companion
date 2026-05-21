# tests/test_shared_model_compat.py

from core.models import DescriptorRecord, FunctionalGroupReport, MoleculeRecord
from core.descriptor_utils import compute_descriptors
from core.molecule_utils import load_molecule
from spectra.functional_group_detector import FGReport, FunctionalGroupDetector


def test_load_molecule_returns_shared_molecule_record():
    record = load_molecule(smiles="CCO")
    assert isinstance(record, MoleculeRecord)
    assert isinstance(record.to_dict(), dict)


def test_compute_descriptors_returns_shared_descriptor_record():
    record = load_molecule(smiles="CCO")
    desc = compute_descriptors(record.rdkit_mol)
    assert isinstance(desc, DescriptorRecord)
    assert isinstance(desc.functional_groups, dict)


def test_fgreport_alias_points_to_shared_model():
    assert FGReport is FunctionalGroupReport


def test_detector_returns_shared_report():
    record = load_molecule(smiles="CC(=O)O")
    report = FunctionalGroupDetector().detect(record.rdkit_mol)
    assert isinstance(report, FunctionalGroupReport)
    assert isinstance(report.counts, dict)
    assert isinstance(report.matches, list)
    assert isinstance(report.todict(), dict)