"""
core/ligand_prep.py
===================
Advanced ligand preparation for docking (Advanced Docking P2).

Adds two things the legacy single-state preparer (core/docking_preparation.py)
does not do:

  1. **Meeko-based PDBQT** — the AutoDock-recommended preparer (correct Gasteiger
     charges, rotatable-bond/torsion-tree perception). Falls back cleanly to the
     existing OpenBabel path when Meeko is unavailable.
  2. **State enumeration** — optional enumeration of protonation states, tautomers,
     stereoisomers, and conformers, so we dock the chemically correct species rather
     than a single arbitrary one. All enumeration is opt-in; the default returns a
     single state and behaves like the legacy preparer.

Nothing here changes the behavior of core/docking_preparation.py — that remains the
zero-config default path.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional

from rdkit import Chem
from rdkit.Chem import MolToSmiles

from core.conversion_utils import embed_3d

logger = logging.getLogger(__name__)

# Safety caps so enumeration never explodes into thousands of docking runs.
_MAX_TAUTOMERS = 4
_MAX_STEREO = 4
_MAX_TOTAL_STATES = 8


@dataclass
class LigandState:
    """One prepared ligand species ready for docking."""
    label: str          # human-readable description of the state
    smiles: str         # canonical isomeric SMILES of this state
    pdbqt: str          # AutoDock PDBQT text
    method: str         # "meeko" | "openbabel"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# SMILES → PDBQT (Meeko preferred, OpenBabel fallback)
# ---------------------------------------------------------------------------

def _mol_to_pdbqt_meeko(mol3d_h: Chem.Mol) -> Optional[str]:
    """Prepare PDBQT via Meeko. Returns None if Meeko is unavailable or fails."""
    try:
        from meeko import MoleculePreparation
    except ImportError:
        return None
    try:
        prep = MoleculePreparation()
        setups = prep.prepare(mol3d_h)
        if not setups:
            return None
        setup = setups[0]
        # Meeko ≥0.5 exposes PDBQTWriterLegacy.write_string; older exposes write_pdbqt_string.
        try:
            from meeko import PDBQTWriterLegacy
            written = PDBQTWriterLegacy.write_string(setup)
            # Returns (pdbqt_string, is_ok, error_msg) in recent versions.
            if isinstance(written, tuple):
                pdbqt, is_ok = written[0], written[1]
                if not is_ok or not pdbqt:
                    return None
                return pdbqt
            return written or None
        except ImportError:
            return prep.write_pdbqt_string()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Meeko ligand preparation failed, will fall back: %s", exc)
        return None


def _mol_to_pdbqt_openbabel(mol3d_h: Chem.Mol) -> str:
    """Prepare PDBQT via the existing OpenBabel path (legacy-equivalent)."""
    from core.openbabel_utils import convert_format
    sdf_block = Chem.MolToMolBlock(mol3d_h)
    pdbqt = convert_format(sdf_block, "sdf", "pdbqt").strip()
    if not pdbqt:
        raise RuntimeError("OpenBabel produced empty PDBQT for ligand.")
    return pdbqt


def _prepare_single(mol: Chem.Mol, label: str, prefer_meeko: bool, seed: int) -> Optional[LigandState]:
    """Embed one RDKit mol in 3D and write PDBQT."""
    try:
        mol3d = embed_3d(mol, optimize=True, random_seed=seed)  # returns mol with Hs
    except Exception as exc:  # noqa: BLE001
        logger.warning("3D embedding failed for state '%s': %s", label, exc)
        return None

    smiles = MolToSmiles(Chem.RemoveHs(mol3d), canonical=True)

    pdbqt = None
    method = "openbabel"
    if prefer_meeko:
        pdbqt = _mol_to_pdbqt_meeko(mol3d)
        if pdbqt:
            method = "meeko"
    if not pdbqt:
        try:
            pdbqt = _mol_to_pdbqt_openbabel(mol3d)
        except Exception as exc:  # noqa: BLE001
            logger.warning("PDBQT write failed for state '%s': %s", label, exc)
            return None

    return LigandState(label=label, smiles=smiles, pdbqt=pdbqt, method=method)


# ---------------------------------------------------------------------------
# State enumeration
# ---------------------------------------------------------------------------

def _base_mol(smiles: str) -> Chem.Mol:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")
    Chem.SanitizeMol(mol)
    # Keep the largest fragment (drop salts/counter-ions).
    frags = Chem.GetMolFrags(mol, asMols=True, sanitizeFrags=True)
    if len(frags) > 1:
        mol = max(frags, key=lambda m: m.GetNumHeavyAtoms())
    return mol


def _enumerate_protonation(smiles: str, ph: float) -> List[str]:
    """Enumerate protonation states with Dimorphite-DL when available; else []."""
    try:
        from dimorphite_dl import DimorphiteDL
    except ImportError:
        logger.info("dimorphite_dl not installed; skipping protonation enumeration.")
        return []
    try:
        dd = DimorphiteDL(min_ph=ph - 0.5, max_ph=ph + 0.5, pka_precision=1.0)
        return list(dd.protonate(smiles))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Protonation enumeration failed: %s", exc)
        return []


def _enumerate_tautomers(mol: Chem.Mol) -> List[str]:
    try:
        from rdkit.Chem.MolStandardize import rdMolStandardize
        enumerator = rdMolStandardize.TautomerEnumerator()
        tauts = enumerator.Enumerate(mol)
        return [MolToSmiles(t, canonical=True) for t in list(tauts)[:_MAX_TAUTOMERS]]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Tautomer enumeration failed: %s", exc)
        return []


def _enumerate_stereo(mol: Chem.Mol) -> List[str]:
    try:
        from rdkit.Chem.EnumerateStereoisomers import (
            EnumerateStereoisomers, StereoEnumerationOptions,
        )
        opts = StereoEnumerationOptions(maxIsomers=_MAX_STEREO, onlyUnassigned=True)
        isomers = list(EnumerateStereoisomers(mol, options=opts))
        return [MolToSmiles(m, canonical=True, isomericSmiles=True) for m in isomers]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Stereoisomer enumeration failed: %s", exc)
        return []


def prepare_ligand_states(
    smiles: str,
    *,
    ph: Optional[float] = None,
    enumerate_protonation: bool = False,
    enumerate_tautomers: bool = False,
    enumerate_stereo: bool = False,
    n_conformers: int = 1,
    prefer_meeko: bool = True,
) -> List[LigandState]:
    """Prepare one or more docking-ready ligand states from a SMILES string.

    With all flags default (off) this returns a single canonical state, using Meeko
    if available and OpenBabel otherwise — a drop-in richer replacement for the
    legacy single-state preparer.
    """
    if not isinstance(smiles, str) or not smiles.strip():
        raise ValueError("SMILES must be a non-empty string.")

    base = _base_mol(smiles)
    base_smiles = MolToSmiles(base, canonical=True)

    # Collect candidate (label, smiles) pairs, de-duplicated, capped.
    candidates: List[tuple[str, str]] = [("canonical", base_smiles)]

    if enumerate_protonation and ph is not None:
        for i, s in enumerate(_enumerate_protonation(base_smiles, ph)):
            candidates.append((f"protomer@pH{ph:g}#{i + 1}", s))

    if enumerate_tautomers:
        for i, s in enumerate(_enumerate_tautomers(base)):
            candidates.append((f"tautomer#{i + 1}", s))

    if enumerate_stereo:
        for i, s in enumerate(_enumerate_stereo(base)):
            candidates.append((f"stereo#{i + 1}", s))

    # De-duplicate by canonical SMILES, keeping first label; cap total.
    seen: set[str] = set()
    unique: List[tuple[str, str]] = []
    for label, smi in candidates:
        try:
            canon = MolToSmiles(Chem.MolFromSmiles(smi), canonical=True)
        except Exception:  # noqa: BLE001
            continue
        if canon in seen:
            continue
        seen.add(canon)
        unique.append((label, canon))
        if len(unique) >= _MAX_TOTAL_STATES:
            break

    states: List[LigandState] = []
    for label, smi in unique:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            continue
        Chem.SanitizeMol(mol)
        n_conf = max(1, int(n_conformers))
        for c in range(n_conf):
            conf_label = label if n_conf == 1 else f"{label}/conf{c + 1}"
            state = _prepare_single(mol, conf_label, prefer_meeko, seed=42 + c)
            if state is not None:
                states.append(state)

    if not states:
        raise RuntimeError(f"Ligand preparation produced no usable states for: {smiles}")

    logger.info("Prepared %d ligand state(s) for %s", len(states), base_smiles)
    return states


__all__ = ["LigandState", "prepare_ligand_states"]
