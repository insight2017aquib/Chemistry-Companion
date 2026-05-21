"""Resolve IUPAC/common names to SMILES and validate with RDKit.

Tries PubChem (PubChemPy + REST fallback) then OPSIN REST.

Example usage: run the script or call `resolve_name_to_mol(name)` from Python.
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple
from urllib.parse import quote

import pubchempy as pcp
import requests
from rdkit import Chem

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def resolve_name_to_smiles(name: str, timeout: int = 8) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
    """Resolve a chemical name to a SMILES string.

    Returns (success, smiles_or_None, source_or_None, error_or_None).
    """
    text = (name or "").strip()
    if not text:
        return False, None, None, "Empty name provided"

    # 1) Try PubChemPy
    try:
        logger.debug("Trying PubChemPy for name: %s", text)
        compounds = pcp.get_compounds(text, "name")
        if compounds:
            comp = compounds[0]
            smiles = getattr(comp, "canonical_smiles", None) or getattr(comp, "isomeric_smiles", None) or getattr(comp, "smiles", None)
            if smiles:
                return True, smiles, "pubchempy", None
    except Exception as exc:
        logger.debug("PubChemPy lookup failed: %s", exc)

    # 2) PubChem REST fallback
    try:
        logger.debug("Trying PubChem REST for name: %s", text)
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{quote(text)}/property/CanonicalSMILES/JSON"
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        props = data.get("PropertyTable", {}).get("Properties", [])
        if props:
            smiles = props[0].get("CanonicalSMILES")
            if smiles:
                return True, smiles, "pubchem-rest", None
    except Exception as exc:
        logger.debug("PubChem REST lookup failed: %s", exc)

    # 3) OPSIN REST
    try:
        logger.debug("Trying OPSIN for name: %s", text)
        opsin_url = f"https://opsin.ch.cam.ac.uk/opsin/{quote(text)}.smiles"
        resp = requests.get(opsin_url, timeout=timeout)
        if resp.status_code == 200 and resp.text:
            smiles = resp.text.strip()
            return True, smiles, "opsin", None
    except Exception as exc:
        logger.debug("OPSIN lookup failed: %s", exc)

    # 4) CACTUS (NCI) resolver fallback
    try:
        logger.debug("Trying CACTUS for name: %s", text)
        cactus_url = f"https://cactus.nci.nih.gov/chemical/structure/{quote(text)}/smiles"
        resp = requests.get(cactus_url, timeout=timeout)
        if resp.status_code == 200 and resp.text:
            smiles = resp.text.strip()
            return True, smiles, "cactus", None
    except Exception as exc:
        logger.debug("CACTUS lookup failed: %s", exc)

    return False, None, None, "Could not resolve name via PubChem or OPSIN"


def smiles_to_rdkit_mol(smiles: str) -> Tuple[bool, Optional[Chem.Mol], Optional[str]]:
    """Parse SMILES with RDKit and sanitize.

    Returns (success, mol_or_None, error_or_None)
    """
    if not smiles:
        return False, None, "Empty SMILES"
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return False, None, f"RDKit could not parse SMILES: {smiles}"
        try:
            Chem.SanitizeMol(mol)
        except Exception:
            # Some molecules may sanitize with warnings; try a relaxed approach
            try:
                Chem.SanitizeMol(mol, Chem.SANITIZE_ALL ^ Chem.SANITIZE_KEKULIZE)
            except Exception:
                # final fallback: return mol even if sanitization failed
                logger.debug("Sanitization failed for SMILES: %s", smiles, exc_info=True)
        return True, mol, None
    except Exception as exc:
        return False, None, str(exc)


def resolve_name_to_mol(name: str, timeout: int = 8) -> Tuple[bool, Optional[Chem.Mol], Optional[str], Optional[str]]:
    """High-level helper: name -> SMILES -> RDKit Mol. Returns (success, mol, smiles, error).
    """
    ok, smiles, source, err = resolve_name_to_smiles(name, timeout=timeout)
    if not ok:
        return False, None, None, err

    ok2, mol, err2 = smiles_to_rdkit_mol(smiles)
    if not ok2:
        return False, None, smiles, err2

    return True, mol, smiles, None


if __name__ == "__main__":
    test_name = "N-(3-chloro-2-(naphthalen-1-yl)-4-oxoazetidin-1-yl)-3-hydroxyquinoxaline-2-carboxamide"
    print("Resolving:", test_name)
    success, mol, smiles, error = resolve_name_to_mol(test_name)
    if success:
        canonical = Chem.MolToSmiles(mol, canonical=True)
        print("Success:\n  Source SMILES:", smiles)
        print("  RDKit canonical SMILES:", canonical)
    else:
        print("Resolution failed:", error)
