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
from typing import Literal, Optional

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
    ph: Optional[float] = None,
) -> str:
    """Prepare a docking-ready ligand from SMILES and export it as a formatted string.

    The workflow is:
      1. Validate and canonicalize SMILES with RDKit
      2. Strip counter-ions/salts, keeping only the largest fragment
      3. Optionally correct the ionization state for a target pH with Open Babel
      4. Generate 3D coordinates with Open Babel
      5. Optimize geometry with Open Babel
      6. Optionally add hydrogens and export to PDBQT
    """
    rdkit_mol = _validate_smiles(smiles)
    canonical_smiles = MolToSmiles(rdkit_mol, canonical=True)
    logger.info("Docking preparation started for SMILES: %s", canonical_smiles)

    from core.conversion_utils import embed_3d
    from core.openbabel_utils import convert_format, adjust_ph, remove_salts

    if "." in canonical_smiles:
        try:
            stripped_smiles = remove_salts(canonical_smiles, input_format="smi", output_format="smi")
            stripped_mol = Chem.MolFromSmiles(stripped_smiles)
            if stripped_mol is not None:
                Chem.SanitizeMol(stripped_mol)
                rdkit_mol = stripped_mol
                canonical_smiles = MolToSmiles(rdkit_mol, canonical=True)
                logger.info("Stripped salts/counter-ions; docking the largest fragment: %s", canonical_smiles)
            else:
                logger.warning(
                    "Salt-stripped SMILES could not be re-parsed by RDKit; "
                    "docking the original multi-component input as-is."
                )
        except Exception as exc:
            logger.warning("Salt stripping failed (%s); docking the original multi-component input as-is.", exc)

    if ph is not None:
        try:
            protonated_smiles = adjust_ph(canonical_smiles, input_format="smi", output_format="smi", ph=ph)
            protonated_mol = Chem.MolFromSmiles(protonated_smiles)
            if protonated_mol is not None:
                Chem.SanitizeMol(protonated_mol)
                rdkit_mol = protonated_mol
                canonical_smiles = MolToSmiles(rdkit_mol, canonical=True)
                logger.info("Applied pH %.1f ionization correction: %s", ph, canonical_smiles)
            else:
                logger.warning(
                    "pH-corrected SMILES could not be re-parsed by RDKit; "
                    "docking with the original (uncorrected) ionization state."
                )
        except Exception as exc:
            logger.warning("pH correction failed (%s); using original ionization state.", exc)

    # Generate 3D coordinates and optimize using RDKit (more robust than Open Babel's OBBuilder)
    mol3d = embed_3d(rdkit_mol, optimize=True)
    
    # Generate SDF block
    sdf_block = Chem.MolToMolBlock(mol3d)

    fmt = output_format.strip().lower()
    if fmt not in _SUPPORTED_OUTPUT_FORMATS:
        raise ValueError(
            f"Unsupported docking output format: {output_format}. "
            f"Supported formats: {sorted(_SUPPORTED_OUTPUT_FORMATS)}"
        )

    try:
        docking_string = convert_format(sdf_block, "sdf", fmt)
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
