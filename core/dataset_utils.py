"""
chemistry_companion/core/dataset_utils.py
==========================================
Dataset utilities for Chemistry Companion.

Features
- Load molecular datasets from CSV, Excel (.xlsx/.xls), and SDF
- SMILES validation
- Molecule standardization (salt stripping, canonicalization)
- Optional RDKit MolStandardize normalization when available
- Duplicate removal by canonical SMILES or InChIKey
- Descriptor table generation (delegates to core.descriptor_utils)
- pandas + RDKit integration, type hints, logging, robust error handling
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import pandas as pd
from rdkit import Chem
from rdkit.Chem import SaltRemover

try:
    from rdkit.Chem.MolStandardize import rdMolStandardize
    _HAS_MOLSTANDARDIZE = True
except Exception:
    _HAS_MOLSTANDARDIZE = False

try:
    from rdkit.Chem.inchi import MolToInchiKey
    _HAS_INCHI = True
except Exception:
    _HAS_INCHI = False

from core.descriptor_utils import compute_descriptors

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

DedupMethod = Literal["canonical_smiles", "inchikey"]

HEURISTIC_DISCLAIMER = "HEURISTIC ONLY — approximate descriptors, not experimental values."


# ──────────────────────────────────────────────────────────────────────────────
# Custom exception
# ──────────────────────────────────────────────────────────────────────────────

class DatasetLoadError(RuntimeError):
    """Raised when a dataset file cannot be loaded or parsed."""


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _read_tabular(path: Path, **kwargs: Any) -> pd.DataFrame:
    ext = path.suffix.lower()
    try:
        if ext in {".csv", ".tsv"}:
            df = pd.read_csv(path, **kwargs)
        elif ext in {".xls", ".xlsx"}:
            df = pd.read_excel(path, **kwargs)
        else:
            raise DatasetLoadError(f"Unsupported tabular format: {ext}")
    except DatasetLoadError:
        raise
    except Exception as exc:
        logger.exception("Failed to read %s: %s", path, exc)
        raise DatasetLoadError(f"Could not read file {path}: {exc}") from exc
    return df


def _load_sdf(path: Path) -> pd.DataFrame:
    """Load an SDF with graceful per-molecule fallback sanitisation."""
    supplier = Chem.SDMolSupplier(str(path), sanitize=False, removeHs=False)
    rows: List[Dict[str, str]] = []
    for i, mol in enumerate(supplier):
        if mol is None:
            logger.debug("SDF: skipped None molecule at index %d", i)
            continue
        try:
            Chem.SanitizeMol(mol)
        except Exception:
            try:
                Chem.SanitizeMol(mol, Chem.SANITIZE_ALL ^ Chem.SANITIZE_KEKULIZE)
            except Exception:
                logger.debug("SDF: could not sanitize molecule at index %d", i)
        try:
            smiles = Chem.MolToSmiles(mol, isomericSmiles=True) or ""
        except Exception:
            smiles = ""
        name = mol.GetProp("_Name") if mol.HasProp("_Name") else ""
        rows.append({"smiles": smiles, "name": name})
    if not rows:
        raise DatasetLoadError(f"No valid molecules found in SDF: {path}")
    return pd.DataFrame(rows)


def _canonical_smiles_from_mol(mol: Chem.Mol) -> Optional[str]:
    try:
        mol2 = Chem.RemoveHs(mol)
        return Chem.MolToSmiles(mol2, isomericSmiles=True, canonical=True)
    except Exception as exc:
        logger.debug("Canonicalization failed: %s", exc)
        return None


def _inchikey_from_smiles(smiles: str) -> Optional[str]:
    if not _HAS_INCHI:
        return None
    try:
        mol = Chem.MolFromSmiles(smiles)
        return MolToInchiKey(mol) if mol else None
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# 1. Loading
# ──────────────────────────────────────────────────────────────────────────────

def load_molecular_dataset(
    path: Union[str, Path],
    smiles_col: str = "SMILES",
    name_col: Optional[str] = None,
    **reader_kwargs: Any,
) -> pd.DataFrame:
    """
    Load a molecular dataset from CSV, Excel, or SDF.

    Returns a DataFrame with at least a ``smiles`` column and
    optional ``name`` column. Raises ``DatasetLoadError`` on failure.
    """
    p = Path(path)
    if not p.exists():
        raise DatasetLoadError(f"File not found: {p}")

    ext = p.suffix.lower()
    if ext in {".csv", ".tsv", ".xls", ".xlsx"}:
        df = _read_tabular(p, **reader_kwargs)
        cols_lower = {c.lower(): c for c in df.columns}
        if smiles_col.lower() in cols_lower:
            df = df.rename(columns={cols_lower[smiles_col.lower()]: "smiles"})
        elif df.shape[1] == 1:
            df = df.rename(columns={df.columns[0]: "smiles"})
        else:
            raise DatasetLoadError(
                f"No SMILES column ('{smiles_col}') found in {p}. "
                f"Available columns: {list(df.columns)}"
            )
        if name_col and name_col.lower() in cols_lower:
            df = df.rename(columns={cols_lower[name_col.lower()]: "name"})
        df["smiles"] = df["smiles"].astype(str).str.strip().fillna("")
        if "name" in df.columns:
            df["name"] = df["name"].astype(str).fillna("")
        keep = ["smiles", "name"] if "name" in df.columns else ["smiles"]
        logger.info("Loaded %d rows from %s", len(df), p)
        return df[keep]

    if ext in {".sdf", ".sd"}:
        df = _load_sdf(p)
        logger.info("Loaded %d molecules from SDF %s", len(df), p)
        return df

    raise DatasetLoadError(f"Unsupported file type: {ext}")


# ──────────────────────────────────────────────────────────────────────────────
# 2. Validation
# ──────────────────────────────────────────────────────────────────────────────

def validate_smiles(smiles: str) -> bool:
    """Return True if RDKit can parse the SMILES and the molecule is non-empty."""
    if not isinstance(smiles, str) or not smiles.strip():
        return False
    try:
        mol = Chem.MolFromSmiles(smiles, sanitize=True)
        return mol is not None and mol.GetNumAtoms() > 0
    except Exception:
        return False


# ──────────────────────────────────────────────────────────────────────────────
# 3. Standardisation
# ──────────────────────────────────────────────────────────────────────────────

def standardize_molecule(smiles: str, use_molstandardize: bool = True) -> Optional[str]:
    """
    Standardise a single SMILES string:
    1. Parse
    2. Optional MolStandardize normalization + reionization
    3. Salt stripping (SaltRemover)
    4. Canonical SMILES generation

    Returns canonical SMILES or None on failure.
    """
    if not isinstance(smiles, str) or not smiles.strip():
        return None
    try:
        mol = Chem.MolFromSmiles(smiles, sanitize=True)
        if mol is None:
            return None

        if use_molstandardize and _HAS_MOLSTANDARDIZE:
            try:
                mol = rdMolStandardize.Normalizer().normalize(mol)
                mol = rdMolStandardize.Reionizer().reionize(mol)
            except Exception as exc:
                logger.debug("MolStandardize normalization failed: %s", exc)

        try:
            mol = SaltRemover.SaltRemover().StripMol(mol)
        except Exception:
            logger.debug("SaltRemover failed for: %s", smiles)

        if mol is None or mol.GetNumAtoms() == 0:
            return None

        return _canonical_smiles_from_mol(mol)
    except Exception as exc:
        logger.debug("standardize_molecule failed for %r: %s", smiles, exc)
        return None


def standardize_dataset(
    df: pd.DataFrame,
    smiles_col: str = "smiles",
    use_molstandardize: bool = True,
) -> pd.DataFrame:
    """
    Add ``standardized_smiles`` column and drop rows that fail standardisation.
    """
    if smiles_col not in df.columns:
        raise ValueError(f"DataFrame missing required column: '{smiles_col}'")
    df = df.copy()
    df["standardized_smiles"] = df[smiles_col].apply(
        lambda s: standardize_molecule(s, use_molstandardize=use_molstandardize)
    )
    before = len(df)
    df = df.dropna(subset=["standardized_smiles"]).reset_index(drop=True)
    logger.info("Standardised: %d → %d valid molecules (%d dropped)", before, len(df), before - len(df))
    return df


# ──────────────────────────────────────────────────────────────────────────────
# 4. Duplicate removal
# ──────────────────────────────────────────────────────────────────────────────

def remove_duplicate_molecules(
    df: pd.DataFrame,
    smiles_col: str = "standardized_smiles",
    method: DedupMethod = "canonical_smiles",
    keep: Literal["first", "last"] = "first",
) -> pd.DataFrame:
    """
    Remove duplicate molecules by canonical SMILES or InChIKey.

    Parameters
    ----------
    method : ``"canonical_smiles"`` or ``"inchikey"``
        InChIKey is more robust (handles tautomers) but requires RDKit InChI support.
    keep : ``"first"`` or ``"last"``
    """
    if smiles_col not in df.columns:
        raise ValueError(f"DataFrame missing required column: '{smiles_col}'")
    if method not in {"canonical_smiles", "inchikey"}:
        raise ValueError(f"method must be 'canonical_smiles' or 'inchikey', got '{method}'")

    df = df.copy()
    if method == "inchikey" and _HAS_INCHI:
        df["_dedup_key"] = df[smiles_col].map(_inchikey_from_smiles)
    else:
        if method == "inchikey" and not _HAS_INCHI:
            logger.warning("InChI not available; falling back to canonical_smiles deduplication.")
        df["_dedup_key"] = df[smiles_col]

    before = len(df)
    df = df.drop_duplicates(subset=["_dedup_key"], keep=keep).reset_index(drop=True)
    df = df.drop(columns=["_dedup_key"])
    logger.info("Removed %d duplicate molecules; %d unique remain", before - len(df), len(df))
    return df


# ──────────────────────────────────────────────────────────────────────────────
# 5. Descriptor generation
# ──────────────────────────────────────────────────────────────────────────────

def generate_descriptor_table(
    df: pd.DataFrame,
    smiles_col: str = "standardized_smiles",
    name_col: Optional[str] = "name",
) -> pd.DataFrame:
    """
    Generate descriptors for each molecule via ``core.descriptor_utils.compute_descriptors``.

    Returns the original metadata columns plus descriptor columns:
    mw, logp, tpsa, hbd, hba, rotatable_bonds, ro5_pass.
    Rows that fail descriptor computation return NaN for descriptor columns.
    """
    if smiles_col not in df.columns:
        raise ValueError(f"DataFrame missing required column: '{smiles_col}'")

    DESCRIPTOR_ATTRS = ("mw", "logp", "tpsa", "hbd", "hba", "rotatable_bonds", "ro5_pass")
    records: List[Dict[str, Any]] = []

    for idx, row in df.reset_index(drop=True).iterrows():
        smiles = str(row.get(smiles_col, "") or "")
        name = str(row.get(name_col, f"compound_{idx}") or f"compound_{idx}") if name_col else f"compound_{idx}"
        base: Dict[str, Any] = {"smiles": smiles, "name": name}

        if not smiles:
            logger.debug("Row %d: empty SMILES; skipping descriptors", idx)
            records.append({**base, **{k: None for k in DESCRIPTOR_ATTRS}})
            continue
        try:
            mol = Chem.MolFromSmiles(smiles, sanitize=True)
            if mol is None:
                raise ValueError("RDKit returned None for mol")
            desc = compute_descriptors(mol)
            records.append({**base, **{k: getattr(desc, k, None) for k in DESCRIPTOR_ATTRS}})
        except Exception as exc:
            logger.warning("Descriptor computation failed for row %d (%s): %s", idx, smiles, exc)
            records.append({**base, **{k: None for k in DESCRIPTOR_ATTRS}})

    result = pd.DataFrame(records)
    logger.info("Descriptor table: %d rows × %d columns", *result.shape)
    return result


# ──────────────────────────────────────────────────────────────────────────────
# 6. Convenience pipeline
# ──────────────────────────────────────────────────────────────────────────────

def process_molecular_dataset(
    path: Union[str, Path],
    smiles_col: str = "SMILES",
    name_col: Optional[str] = None,
    remove_duplicates_flag: bool = True,
    dedup_method: DedupMethod = "canonical_smiles",
    generate_descriptors_flag: bool = True,
    use_molstandardize: bool = True,
) -> pd.DataFrame:
    """
    End-to-end pipeline:

        load → validate → standardize → deduplicate → descriptors

    Returns a descriptor table DataFrame if ``generate_descriptors_flag`` is
    True, otherwise the standardized/deduplicated DataFrame.
    """
    df = load_molecular_dataset(path, smiles_col=smiles_col, name_col=name_col)

    df = df[df["smiles"].apply(validate_smiles)].reset_index(drop=True)
    logger.info("After SMILES validation: %d molecules", len(df))

    df = standardize_dataset(df, smiles_col="smiles", use_molstandardize=use_molstandardize)

    if remove_duplicates_flag:
        df = remove_duplicate_molecules(
            df, smiles_col="standardized_smiles", method=dedup_method
        )

    if generate_descriptors_flag:
        return generate_descriptor_table(
            df, smiles_col="standardized_smiles", name_col=name_col or "name"
        )
    return df


__all__ = [
    "DatasetLoadError",
    "DedupMethod",
    "HEURISTIC_DISCLAIMER",
    "generate_descriptor_table",
    "load_molecular_dataset",
    "process_molecular_dataset",
    "remove_duplicate_molecules",
    "standardize_dataset",
    "standardize_molecule",
    "validate_smiles",
]