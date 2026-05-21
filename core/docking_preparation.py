"""
core/docking_preparation.py
===========================
Open Babel docking preparation workflow.

This module prepares small-molecule ligands for AutoDock-compatible docking
by converting valid SMILES input into optimized 3D structures and exporting
AutoDock-compatible PDBQT representations.

RDKit is used for SMILES validation and canonicalization; Open Babel is used for
3D generation, geometry optimization, and PDBQT export.
"""

from __future__ import annotations

import logging
from typing import Literal

from rdkit import Chem
from rdkit.Chem import MolToSmiles

from core.openbabel_utils import generate_3d_coordinates, optimize_geometry

logger = logging.getLogger(__name__)

_SUPPORTED_OUTPUT_FORMATS = {
    "pdbqt",
    "pdb",
    "mol2",
    "sdf",
    "xyz",
    "mol",
    "smi",
}


def _validate_smiles(smiles: str) -> Chem.Mol:
    if not isinstance(smiles, str) or not smiles.strip():
        raise ValueError("SMILES must be a non-empty string.")
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES input: {smiles}")
    Chem.SanitizeMol(mol)
    return mol


def prepare_docking_structure(
    smiles: str,
    *,
    output_format: Literal["pdbqt", "pdb", "mol2", "sdf", "xyz", "mol", "smi"] = "pdbqt",
    optimization_method: str = "uff",
    optimization_steps: int = 250,
    add_hydrogens: bool = True,
) -> str:
    """Prepare a docking-ready ligand from SMILES and export it as a formatted string.

    The workflow is:
      1. Validate and canonicalize SMILES with RDKit
      2. Generate 3D coordinates with Open Babel
      3. Optimize geometry with Open Babel
      4. Optionally add hydrogens and export to PDBQT
    """
    rdkit_mol = _validate_smiles(smiles)
    canonical_smiles = MolToSmiles(rdkit_mol, canonical=True)
    logger.info("Docking preparation started for SMILES: %s", canonical_smiles)

    ob_molecule = generate_3d_coordinates(canonical_smiles, input_format="smi")
    optimized = optimize_geometry(
        ob_molecule,
        method=optimization_method,
        steps=optimization_steps,
    )

    if add_hydrogens:
        optimized.addh()

    fmt = output_format.strip().lower()
    if fmt not in _SUPPORTED_OUTPUT_FORMATS:
        raise ValueError(
            f"Unsupported docking output format: {output_format}. "
            f"Supported formats: {sorted(_SUPPORTED_OUTPUT_FORMATS)}"
        )

    try:
        docking_string = optimized.write(fmt)
    except Exception as exc:
        raise RuntimeError(
            f"Open Babel failed to write docking structure as {fmt}: {exc}"
        ) from exc

    docking_string = docking_string.strip()
    if not docking_string:
        raise RuntimeError("Docking structure generation produced empty output.")

    logger.info("Docking structure prepared successfully as %s", fmt)
    return docking_string


__all__ = ["prepare_docking_structure"]
