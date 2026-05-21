"""
core/molecule_utils.py
======================
Utilities for parsing molecule inputs and returning a shared MoleculeRecord.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, field_validator
from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors

from core.models import MoleculeRecord


class MoleculeInput(BaseModel):
    smiles: Optional[str] = None
    inchi: Optional[str] = None
    file_path: Optional[str] = None
    iupac_name: Optional[str] = None

    @field_validator("smiles", "inchi", "file_path", "iupac_name", mode="before")
    @classmethod
    def strip_and_none_if_blank(cls, value):
        if value is None:
            return None
        value = str(value).strip()
        return value or None


def mol_from_smiles(smiles: str):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"RDKit could not parse SMILES: {smiles}")
    return mol


def mol_from_inchi(inchi: str):
    mol = Chem.MolFromInchi(inchi)
    if mol is None:
        raise ValueError(f"Invalid InChI: {inchi}")
    return mol


def mol_from_file(file_path: str):
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(file_path)

    suffix = path.suffix.lower()
    if suffix == ".mol":
        mol = Chem.MolFromMolFile(str(path))
    elif suffix == ".sdf":
        supplier = Chem.SDMolSupplier(str(path))
        mol = next((m for m in supplier if m is not None), None)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    if mol is None:
        raise ValueError(f"Could not parse molecule from file: {file_path}")
    return mol


def mol_from_iupac(iupac_name: str):
    # Use the centralized resolver which handles caching, timeouts and validation.
    from core.resolver import resolve_molecule_input

    res = resolve_molecule_input(iupac_name)
    if not res.success or res.rdkit_mol is None:
        raise ValueError(f"Could not resolve IUPAC/common name: {iupac_name} ({res.error})")
    return res.rdkit_mol


def count_atoms(mol) -> dict[str, int]:
    mol_h = Chem.AddHs(mol)
    counts: dict[str, int] = {}
    for atom in mol_h.GetAtoms():
        symbol = atom.GetSymbol()
        counts[symbol] = counts.get(symbol, 0) + 1
    return counts


def is_aromatic(mol) -> bool:
    return any(atom.GetIsAromatic() for atom in mol.GetAtoms())


def build_record(mol, *, name: str | None = None) -> MoleculeRecord:
    smiles = Chem.MolToSmiles(mol)
    try:
        inchi = Chem.MolToInchi(mol)
    except Exception:
        inchi = None

    try:
        inchikey = Chem.InchiToInchiKey(inchi) if inchi else None
    except Exception:
        inchikey = None

    try:
        formula = rdMolDescriptors.CalcMolFormula(mol)
    except Exception:
        formula = None

    return MoleculeRecord(
        smiles=smiles,
        inchi=inchi,
        inchikey=inchikey,
        name=name,
        formula=formula,
        mol_weight=float(Descriptors.MolWt(mol)),
        exact_mass=float(rdMolDescriptors.CalcExactMolWt(mol)),
        atom_counts=count_atoms(mol),
        num_atoms=int(Chem.AddHs(mol).GetNumAtoms()),
        num_heavy_atoms=int(mol.GetNumHeavyAtoms()),
        num_bonds=int(mol.GetNumBonds()),
        num_rings=int(rdMolDescriptors.CalcNumRings(mol)),
        is_aromatic=is_aromatic(mol),
        rdkit_mol=mol,
    )


def load_molecule(
    smiles: Optional[str] = None,
    inchi: Optional[str] = None,
    file_path: Optional[str] = None,
    iupac_name: Optional[str] = None,
) -> MoleculeRecord:
    inputs = MoleculeInput(
        smiles=smiles,
        inchi=inchi,
        file_path=file_path,
        iupac_name=iupac_name,
    )

    provided_values = [inputs.smiles, inputs.inchi, inputs.file_path, inputs.iupac_name]
    provided = sum(value is not None for value in provided_values)

    if provided == 0:
        raise ValueError(
            "No input provided. Supply exactly one of: smiles, inchi, file_path, iupac_name."
        )

    if provided > 1:
        raise ValueError(
            f"Multiple inputs provided ({provided}). "
            "Supply exactly one of: smiles, inchi, file_path, iupac_name."
        )

    if inputs.smiles is not None:
        # First try direct SMILES parsing; if that fails, attempt to resolve
        # the input using the resolver (handles names/inchi fallbacks).
        try:
            mol = mol_from_smiles(inputs.smiles)
            return build_record(mol)
        except ValueError:
            # Try resolver which will attempt SMILES->InChI->PubChem
            from core.resolver import resolve_molecule_input

            res = resolve_molecule_input(inputs.smiles)
            if not res.success or res.rdkit_mol is None:
                raise ValueError(f"Invalid SMILES or could not resolve input: {inputs.smiles} ({res.error})")
            return build_record(res.rdkit_mol, name=None)

    if inputs.inchi is not None:
        mol = mol_from_inchi(inputs.inchi)
        return build_record(mol)

    if inputs.file_path is not None:
        mol = mol_from_file(inputs.file_path)
        return build_record(mol)

    mol = mol_from_iupac(inputs.iupac_name)
    return build_record(mol, name=inputs.iupac_name)


__all__ = [
    "MoleculeInput",
    "MoleculeRecord",
    "mol_from_smiles",
    "mol_from_inchi",
    "mol_from_file",
    "mol_from_iupac",
    "count_atoms",
    "is_aromatic",
    "build_record",
    "load_molecule",
]