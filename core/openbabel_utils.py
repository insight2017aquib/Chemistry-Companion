"""
core/openbabel_utils.py
=======================
Open Babel interoperability and preprocessing utilities.

This module supplements RDKit by providing format conversion, hydrogen state
management, pH correction, and 3D coordinate generation. It explicitly avoids
computing descriptors, spectra, or SMARTS matching.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any, Iterable, List

try:
    from openbabel import openbabel, pybel
    _HAS_OPENBABEL = True
except ImportError:
    openbabel = None
    pybel = None
    _HAS_OPENBABEL = False

def _check_openbabel():
    if not _HAS_OPENBABEL:
        raise RuntimeError("Open Babel is not available.")

logger = logging.getLogger(__name__)

_FORMAT_ALIAS_MAP = {
    "smiles": "smi",
    "smi": "smi",
    "inchi": "inchi",
    "mol": "mol",
    "molfile": "mol",
    "sdf": "sdf",
    "sd": "sdf",
    "mol2": "mol2",
    "pdb": "pdb",
    "pdbqt": "pdbqt",
    "xyz": "xyz",
}

_SUPPORTED_OUTPUT_FORMATS = {
    "smi",
    "mol",
    "mol2",
    "pdb",
    "pdbqt",
    "sdf",
    "xyz",
}

_SUPPORTED_INPUT_FORMATS = _SUPPORTED_OUTPUT_FORMATS | {"inchi"}


def _normalize_format(fmt: str) -> str:
    if fmt is None:
        raise ValueError("Format name is required.")
    key = str(fmt).strip().lower()
    if key in _FORMAT_ALIAS_MAP:
        normalized = _FORMAT_ALIAS_MAP[key]
    else:
        normalized = key
    if normalized not in _SUPPORTED_INPUT_FORMATS:
        raise ValueError(
            f"Unsupported Open Babel format: {fmt!r}. "
            f"Supported formats: {sorted(_SUPPORTED_INPUT_FORMATS)}"
        )
    return normalized


def _read_molecules(input_data: str, input_format: str) -> list[pybel.Molecule]:
    _check_openbabel()
    input_format = _normalize_format(input_format)
    if input_format == "inchi":
        from core.conversion_utils import inchi_to_molblock

        input_data = inchi_to_molblock(input_data)
        input_format = "mol"

    if input_format == "sdf":
        with tempfile.NamedTemporaryFile("w", suffix=".sdf", delete=False, encoding="utf-8") as tmp:
            tmp.write(input_data)
            tmp.flush()
            temp_path = Path(tmp.name)
        try:
            molecules = list(pybel.readfile("sdf", str(temp_path)))
        finally:
            try:
                temp_path.unlink()
            except OSError:
                pass
        if not molecules:
            raise ValueError("No molecules were parsed from SDF input.")
        return molecules

    try:
        molecule = pybel.readstring(input_format, input_data)
    except Exception:
        with tempfile.NamedTemporaryFile("w", suffix=f".{input_format}", delete=False, encoding="utf-8") as tmp:
            tmp.write(input_data)
            tmp.flush()
            temp_path = Path(tmp.name)
        try:
            molecules = list(pybel.readfile(input_format, str(temp_path)))
        finally:
            try:
                temp_path.unlink()
            except OSError:
                pass
        if not molecules:
            raise ValueError(
                f"Open Babel failed to parse input as {input_format}."
            )
        return molecules
    if molecule is None or molecule.OBMol.NumAtoms() == 0:
        with tempfile.NamedTemporaryFile("w", suffix=f".{input_format}", delete=False, encoding="utf-8") as tmp:
            tmp.write(input_data)
            tmp.flush()
            temp_path = Path(tmp.name)
        try:
            molecules = list(pybel.readfile(input_format, str(temp_path)))
        finally:
            try:
                temp_path.unlink()
            except OSError:
                pass
        if not molecules:
            raise ValueError(f"No atoms could be parsed from {input_format} input.")
        return molecules
    return [molecule]


def _write_molecule(molecule: pybel.Molecule, output_format: str) -> str:
    _check_openbabel()
    output_format = _normalize_format(output_format)
    if output_format not in _SUPPORTED_OUTPUT_FORMATS:
        raise ValueError(f"Unsupported Open Babel output format: {output_format}")

    if output_format in {"pdb", "pdbqt", "xyz"} and molecule.OBMol.NumConformers() == 0:
        molecule = generate_3d_coordinates(molecule)

    try:
        content = molecule.write(output_format)
    except Exception as exc:
        raise ValueError(
            f"Open Babel failed to write molecule as {output_format}: {exc}"
        ) from exc
    content = content.strip()
    if output_format == "smi":
        return content.split()[0]
    return content


def _coerce_molecule_data(value: Any, input_format: str = "smi") -> pybel.Molecule:
    _check_openbabel()
    if isinstance(value, pybel.Molecule):
        return value
    if not isinstance(value, str):
        raise TypeError("Molecule input must be a pybel.Molecule or a string.")
    molecules = _read_molecules(value, input_format)
    return molecules[0]


def convert_format(
    input_data: str,
    input_format: str,
    output_format: str,
) -> str:
    """Convert a molecule representation from one format to another."""
    molecules = _read_molecules(input_data, input_format)
    converted = [
        _write_molecule(molecule, output_format)
        for molecule in molecules
    ]
    return "\n".join(s for s in converted if s)


def smiles_to_mol2(smiles: str) -> str:
    return convert_format(smiles, "smi", "mol2")


def smiles_to_pdbqt(smiles: str) -> str:
    return convert_format(smiles, "smi", "pdbqt")


def mol2_to_smiles(mol2: str) -> str:
    return convert_format(mol2, "mol2", "smi")


def sdf_to_smiles(sdf: str) -> list[str]:
    molecules = _read_molecules(sdf, "sdf")
    return [
        _write_molecule(molecule, "smi")
        for molecule in molecules
    ]


def inchi_to_mol2(inchi: str) -> str:
    return convert_format(inchi, "inchi", "mol2")


def _remove_salts_from_molecule(molecule: pybel.Molecule) -> pybel.Molecule:
    _check_openbabel()
    fragments = molecule.OBMol.Separate()
    if not fragments or len(fragments) <= 1:
        return molecule
    largest = max(fragments, key=lambda mol: (mol.NumHvyAtoms(), mol.NumAtoms()))
    return pybel.Molecule(largest)


def remove_salts(
    input_data: str,
    input_format: str = "smi",
    output_format: str = "smi",
) -> str:
    molecule = _coerce_molecule_data(input_data, input_format)
    stripped = _remove_salts_from_molecule(molecule)
    return _write_molecule(stripped, output_format)


def normalize_structure(
    input_data: str,
    input_format: str = "smi",
    output_format: str = "smi",
    ph: float = 7.0,
) -> str:
    molecule = _coerce_molecule_data(input_data, input_format)
    try:
        molecule.OBMol.CorrectForPH(ph)
    except Exception as exc:
        logger.warning("Open Babel pH correction failed: %s", exc)
    molecule.addh()
    return _write_molecule(molecule, output_format)


def add_hydrogens(
    input_data: str,
    input_format: str = "smi",
    output_format: str = "smi",
) -> str:
    molecule = _coerce_molecule_data(input_data, input_format)
    molecule.addh()
    return _write_molecule(molecule, output_format)


def remove_hydrogens(
    input_data: str,
    input_format: str = "smi",
    output_format: str = "smi",
) -> str:
    molecule = _coerce_molecule_data(input_data, input_format)
    molecule.removeh()
    return _write_molecule(molecule, output_format)


def protonate_structure(
    input_data: str,
    input_format: str = "smi",
    output_format: str = "smi",
    ph: float = 7.4,
) -> str:
    molecule = _coerce_molecule_data(input_data, input_format)
    molecule.addh()
    try:
        molecule.OBMol.CorrectForPH(ph)
    except Exception as exc:
        logger.warning("Open Babel protonation correction failed: %s", exc)
    return _write_molecule(molecule, output_format)


def deprotonate_structure(
    input_data: str,
    input_format: str = "smi",
    output_format: str = "smi",
) -> str:
    molecule = _coerce_molecule_data(input_data, input_format)
    molecule.removeh()
    return _write_molecule(molecule, output_format)


def adjust_ph(
    input_data: str,
    input_format: str = "smi",
    output_format: str = "smi",
    ph: float = 7.4,
) -> str:
    molecule = _coerce_molecule_data(input_data, input_format)
    try:
        molecule.OBMol.CorrectForPH(ph)
    except Exception as exc:
        raise ValueError(f"Open Babel pH adjustment failed: {exc}") from exc
    return _write_molecule(molecule, output_format)


def generate_3d_coordinates(
    input_data: str | pybel.Molecule,
    input_format: str = "smi",
) -> pybel.Molecule:
    _check_openbabel()
    if isinstance(input_data, pybel.Molecule):
        molecule = input_data
    else:
        molecule = _coerce_molecule_data(input_data, input_format)
    try:
        result = molecule.make3D()
    except Exception as exc:
        raise RuntimeError(f"Open Babel 3D coordinate generation failed: {exc}") from exc
    if result is False or molecule.OBMol.NumConformers() == 0:
        raise RuntimeError("3D coordinate generation did not produce a conformer.")
    return molecule


def optimize_geometry(
    input_data: str | pybel.Molecule,
    input_format: str = "smi",
    method: str = "uff",
    steps: int = 250,
) -> pybel.Molecule:
    _check_openbabel()
    if isinstance(input_data, pybel.Molecule):
        molecule = input_data
    else:
        molecule = generate_3d_coordinates(input_data, input_format)

    method = method.strip().lower()
    if method not in {"uff", "mmff94"}:
        raise ValueError("Unsupported optimization method. Choose 'UFF' or 'MMFF94'.")

    molecule.addh()
    try:
        molecule.localopt(forcefield=method, steps=steps)
    except Exception as exc:
        raise RuntimeError(
            f"Open Babel geometry optimization failed using {method}: {exc}"
        ) from exc

    return molecule


__all__ = [
    "convert_format",
    "smiles_to_mol2",
    "smiles_to_pdbqt",
    "mol2_to_smiles",
    "sdf_to_smiles",
    "inchi_to_mol2",
    "remove_salts",
    "normalize_structure",
    "add_hydrogens",
    "remove_hydrogens",
    "protonate_structure",
    "deprotonate_structure",
    "adjust_ph",
    "generate_3d_coordinates",
    "optimize_geometry",
]
