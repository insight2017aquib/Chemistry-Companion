"""
core/descriptor_utils.py
========================
Descriptor calculation utilities returning the shared DescriptorRecord model.
"""

from __future__ import annotations

from typing import Any

from rdkit.Chem import Crippen, Descriptors, Lipinski, rdMolDescriptors

from core.models import DescriptorRecord


class FunctionalGroupCounts(dict):
    def __contains__(self, key: object) -> bool:
        if super().__contains__(key):
            return True
        if not isinstance(key, str):
            return False
        normalized = key.strip().lower().replace(" ", "_")
        for existing in self.keys():
            if existing.lower() == normalized or existing.lower().replace(" ", "_") == normalized:
                return True
        return False

    def get(self, key: object, default=None):
        if super().__contains__(key):
            return super().get(key, default)
        if not isinstance(key, str):
            return default
        normalized = key.strip().lower().replace(" ", "_")
        for existing, value in self.items():
            if existing.lower() == normalized or existing.lower().replace(" ", "_") == normalized:
                return value
        return default

    def __getitem__(self, key: object):
        if super().__contains__(key):
            return super().__getitem__(key)
        if not isinstance(key, str):
            raise KeyError(key)
        normalized = key.strip().lower().replace(" ", "_")
        for existing, value in self.items():
            if existing.lower() == normalized or existing.lower().replace(" ", "_") == normalized:
                return value
        raise KeyError(key)


SMARTS_PATTERNS: dict[str, str] = {
    "alcohol": "[OX2H]",
    "phenol": "c[OX2H]",
    "amine": "[NX3;H2,H1;!$(NC=O)]",
    "amide": "[NX3][CX3](=[OX1])",
    "carboxylic_acid": "C(=O)[OX2H1]",
    "ester": "[#6][CX3](=O)[OX2H0][#6]",
    "ketone": "[#6][CX3](=O)[#6]",
    "aldehyde": "[CX3H1](=O)[#6]",
    "ether": "[OD2]([#6])[#6]",
    "halide": "[F,Cl,Br,I]",
    "nitrile": "[CX2]#N",
    "nitro": "[$([NX3](=O)=O),$([N+](=O)[O-])]",
    "sulfoxide": "[#16X3](=O)",
    "sulfone": "[#16X4](=O)(=O)",
    "thiol": "[#16X2H]",
    "alkene": "C=C",
    "alkyne": "C#C",
    "aromatic_ring": "a1aaaaa1",
}


def load_smarts() -> dict[str, Any]:
    from rdkit import Chem

    compiled: dict[str, Any] = {}
    for name, smarts in SMARTS_PATTERNS.items():
        patt = Chem.MolFromSmarts(smarts)
        if patt is not None:
            compiled[name] = patt
    return compiled


_COMPILED_SMARTS = load_smarts()


def _count_functional_groups(mol) -> FunctionalGroupCounts:
    counts = FunctionalGroupCounts()
    for name, patt in _COMPILED_SMARTS.items():
        try:
            matches = mol.GetSubstructMatches(patt)
            counts[name] = len(matches)
        except Exception:
            counts[name] = 0
    return counts


def compute_descriptors(mol, mw: float | None = None) -> DescriptorRecord:
    if mol is None:
        raise ValueError("Cannot compute descriptors for None molecule.")

    molecular_weight = float(mw) if mw is not None else float(Descriptors.MolWt(mol))

    # CalcBertzCT may not be available in all RDKit versions.
    # Fall back to rdkit.Chem.Descriptors.BertzCT when available.
    try:
        if hasattr(rdMolDescriptors, "CalcBertzCT"):
            bertz_ct = float(rdMolDescriptors.CalcBertzCT(mol))
        elif hasattr(Descriptors, "BertzCT"):
            bertz_ct = float(Descriptors.BertzCT(mol))
        else:
            raise AttributeError("BertzCT is unavailable in installed RDKit")
    except (AttributeError, RuntimeError):
        bertz_ct = None

    return DescriptorRecord(
        molecular_weight=molecular_weight,
        exact_mass=float(rdMolDescriptors.CalcExactMolWt(mol)),
        formula=str(rdMolDescriptors.CalcMolFormula(mol)),
        logp=float(Crippen.MolLogP(mol)),
        tpsa=float(rdMolDescriptors.CalcTPSA(mol)),
        hbd=int(Lipinski.NumHDonors(mol)),
        hba=int(Lipinski.NumHAcceptors(mol)),
        rotatable_bonds=int(Lipinski.NumRotatableBonds(mol)),
        ring_count=int(rdMolDescriptors.CalcNumRings(mol)),
        heavy_atom_count=int(mol.GetNumHeavyAtoms()),
        formal_charge=int(sum(atom.GetFormalCharge() for atom in mol.GetAtoms())),
        fraction_csp3=float(rdMolDescriptors.CalcFractionCSP3(mol)),
        functional_groups=_count_functional_groups(mol),
        bertz_ct=bertz_ct,
    )


def summarise_descriptors(record: DescriptorRecord) -> str:
    groups = [name.replace("_", " ") for name, count in record.functional_groups.items() if count > 0]
    group_text = ", ".join(groups) if groups else "no prominent functional groups detected"

    return (
        f"MW {record.molecular_weight:.2f}; "
        f"LogP {record.logp:.2f}; "
        f"TPSA {record.tpsa:.2f}; "
        f"HBD {record.hbd}; "
        f"HBA {record.hba}; "
        f"rings {record.ring_count}; "
        f"{group_text}."
    )


def get_heterocycles(record: DescriptorRecord) -> dict[str, int]:
    hetero_tokens = ("pyr", "imid", "indol", "quin", "azole", "azine", "thio", "oxa", "aza")
    return {
        key: value
        for key, value in record.functional_groups.items()
        if value > 0 and any(token in key.lower() for token in hetero_tokens)
    }


def summarise_heterocycles(record: DescriptorRecord) -> str:
    heterocycles = get_heterocycles(record)
    if not heterocycles:
        return "No heterocycles detected."
    return ", ".join(f"{k} ({v})" for k, v in heterocycles.items())


def heterocycles_to_records(record: DescriptorRecord) -> list[dict[str, Any]]:
    heterocycles = get_heterocycles(record)
    return [{"group": key, "count": value} for key, value in heterocycles.items()]


def batch_compute_descriptors(mols: list[Any]) -> list[DescriptorRecord]:
    return [compute_descriptors(mol) for mol in mols]


__all__ = [
    "DescriptorRecord",
    "compute_descriptors",
    "summarise_descriptors",
    "get_heterocycles",
    "summarise_heterocycles",
    "heterocycles_to_records",
    "batch_compute_descriptors",
]