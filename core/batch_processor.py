"""
chemistry_companion/core/batch_processor.py
============================================
Production-ready batch processing module for Chemistry Companion.

Features:
- Supports CSV, TXT, and Excel input
- Smart column auto-detection (SMILES prioritized)
- Safe error handling with separate success/error DataFrames
- Optional multiprocessing with deterministic output ordering
- Rate limiting for IUPAC lookups (only when no SMILES provided)
- Heterocycle detection via inline ring analysis (no external dependency)
- BatchResult.summary() convenience method

Fixes applied vs submitted version:
  [FIX-1] get_heterocycles(desc_rec) → inlined on rdkit_mol (ImportError removed)
  [FIX-2] df_success drops status/error columns
  [FIX-3] read_excel_file applies .str.strip() after fillna
  [FIX-4] multiprocessing path sorts entries by row_index after futures complete
  [FIX-5] rate_limit_s applied only when iupac_name AND no smiles present
"""

import csv
import json
import logging
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

import pandas as pd

logger = logging.getLogger(__name__)

# ── Column Detection ──────────────────────────────────────────────────────────

_SMILES_COLUMNS = {
    "smiles", "smi", "canonical_smiles", "smiles_string",
    "structure", "smiles_canonical", "smile",
}
_NAME_COLUMNS = {
    "name", "iupac", "iupac_name", "compound_name", "compound",
    "chemical_name", "molecule_name", "id", "drug_name",
}


# ── Data Models ───────────────────────────────────────────────────────────────

@dataclass
class MoleculeRow:
    """Raw parsed row from an input file."""
    row_index:  int
    smiles:     Optional[str] = None
    iupac_name: Optional[str] = None
    label:      Optional[str] = None
    raw:        dict = field(default_factory=dict)


@dataclass
class ProcessedEntry:
    """Fully computed descriptor record for one molecule."""
    row_index:  int
    input_repr: str
    status:     str                   # "ok" | "error"
    error:      Optional[str] = None

    # Identity
    name:            Optional[str]   = None
    smiles:          Optional[str]   = None
    formula:         Optional[str]   = None
    inchikey:        Optional[str]   = None

    # Physicochemical
    mol_weight:      Optional[float] = None
    exact_mass:      Optional[float] = None
    num_atoms:       Optional[int]   = None
    num_heavy_atoms: Optional[int]   = None
    num_rings:       Optional[int]   = None
    is_aromatic:     Optional[bool]  = None

    # Drug-likeness descriptors
    logp:                  Optional[float] = None
    tpsa:                  Optional[float] = None
    hbd:                   Optional[int]   = None
    hba:                   Optional[int]   = None
    rotatable_bonds:       Optional[int]   = None
    bertz_ct:              Optional[float] = None
    ro5_pass:              Optional[bool]  = None
    ro5_violations:        Optional[int]   = None

    # Annotations
    functional_groups:     Optional[str]   = None   # JSON string
    heterocycles_detected: Optional[int]   = None   # ring count


@dataclass
class BatchResult:
    """
    Container for a completed batch run.

    Attributes:
        entries:    All ProcessedEntry objects (success + error).
        df_success: DataFrame of successful rows (status/error columns removed).
        df_errors:  DataFrame of failed rows with error messages.
        total:      Total molecules attempted.
        n_success:  Number of successful entries.
        n_errors:   Number of failed entries.
        elapsed_s:  Wall-clock seconds for the entire batch.
    """
    entries:    List[ProcessedEntry]
    df_success: pd.DataFrame
    df_errors:  pd.DataFrame
    total:      int
    n_success:  int
    n_errors:   int
    elapsed_s:  float

    def summary(self) -> Dict[str, Any]:
        """Return quick summary statistics as a plain dict."""
        return {
            "total":           self.total,
            "successful":      self.n_success,
            "failed":          self.n_errors,
            "success_rate_%":  round(self.n_success / self.total * 100, 1)
                               if self.total > 0 else 0.0,
            "elapsed_seconds": self.elapsed_s,
        }


# ── Internal Helpers ──────────────────────────────────────────────────────────

def _normalise_header(col: str) -> str:
    return col.strip().lower()


def _detect_columns(columns: List[str]) -> tuple[Optional[str], Optional[str]]:
    """
    Scan column headers and return (smiles_col, name_col).
    Prioritises SMILES; falls back to name-only.
    """
    smiles_col = name_col = None
    for col in columns:
        norm = _normalise_header(col)
        if norm in _SMILES_COLUMNS and smiles_col is None:
            smiles_col = col
        if norm in _NAME_COLUMNS and name_col is None:
            name_col = col
    return smiles_col, name_col


def _count_heterocyclic_rings(rdkit_mol) -> int:
    """
    Count rings containing at least one non-carbon, non-hydrogen atom.
    Inline implementation — no external dependency required.

    Limitation: counts ring *closures* from the SSSR, not unique ring systems.
    For fused systems (caffeine, purine) each ring is counted individually.
    """
    ring_info = rdkit_mol.GetRingInfo()
    count = 0
    for ring in ring_info.AtomRings():
        atoms = [rdkit_mol.GetAtomWithIdx(i) for i in ring]
        if any(a.GetAtomicNum() not in (6, 1) for a in atoms):
            count += 1
    return count


# ── File Readers ──────────────────────────────────────────────────────────────

def read_csv_file(path: str) -> List[MoleculeRow]:
    """
    Parse a CSV/TSV file into MoleculeRow objects.

    Auto-detects SMILES and name columns from headers.
    Uses utf-8-sig encoding to handle Excel-generated BOM.

    Raises:
        ValueError: if file is empty or no usable columns found.
    """
    rows: List[MoleculeRow] = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise ValueError(f"Empty or header-less CSV file: {path}")
        smiles_col, name_col = _detect_columns(list(reader.fieldnames))
        if not smiles_col and not name_col:
            raise ValueError(
                f"No SMILES or name column found in {path}.\n"
                f"Expected one of: {sorted(_SMILES_COLUMNS | _NAME_COLUMNS)}"
            )
        logger.info("CSV — SMILES col: %r  Name col: %r", smiles_col, name_col)
        for i, raw in enumerate(reader, start=1):
            smi  = raw.get(smiles_col, "").strip() if smiles_col else ""
            name = raw.get(name_col,   "").strip() if name_col   else ""
            if not smi and not name:
                continue
            rows.append(MoleculeRow(
                row_index=i,
                smiles=smi or None,
                iupac_name=name or None if not smi else None,
                label=name or smi,
                raw=dict(raw),
            ))
    logger.info("read_csv_file: %d rows parsed from %s", len(rows), path)
    return rows


def read_txt_file(path: str) -> List[MoleculeRow]:
    """
    Parse a plain-text file (one entry per line) into MoleculeRow objects.

    Heuristic: lines containing SMILES characters (()[]=#@\\/%0-9) are
    treated as SMILES; everything else is treated as an IUPAC name.
    Lines starting with '#' are skipped as comments.
    Lines starting with 'InChI=' are skipped with a warning.
    """
    _SMILES_CHARS = set("()[]=#@\\/% 0123456789")
    rows: List[MoleculeRow] = []
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("InChI="):
                logger.warning("Row %d: InChI input not yet supported — skipping.", i)
                continue
            looks_like_smiles = any(c in _SMILES_CHARS for c in line)
            rows.append(MoleculeRow(
                row_index=i,
                smiles=line     if looks_like_smiles else None,
                iupac_name=line if not looks_like_smiles else None,
                label=line,
            ))
    logger.info("read_txt_file: %d rows parsed from %s", len(rows), path)
    return rows


def read_excel_file(path: str, sheet_name: Union[int, str] = 0) -> List[MoleculeRow]:
    """
    Parse an Excel (.xlsx/.xls) file into MoleculeRow objects.

    Applies .str.strip() after fillna to catch leading/trailing whitespace
    from ChemDraw and Reaxys exports (FIX-3).

    Raises:
        ImportError: if openpyxl is not installed.
        ValueError:  if no SMILES or name column is found.
    """
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        raise ImportError(
            "openpyxl is required for Excel input.\n"
            "Install with: pip install openpyxl"
        )

    # FIX-3: apply strip() to all string columns after fillna
    df = (
        pd.read_excel(path, sheet_name=sheet_name, dtype=str)
          .fillna("")
          .apply(lambda col: col.str.strip())
    )
    smiles_col, name_col = _detect_columns(list(df.columns))
    if not smiles_col and not name_col:
        raise ValueError(
            f"No SMILES or name column found in {path}.\n"
            f"Expected one of: {sorted(_SMILES_COLUMNS | _NAME_COLUMNS)}"
        )
    logger.info("Excel — SMILES col: %r  Name col: %r", smiles_col, name_col)

    rows: List[MoleculeRow] = []
    for i, row in df.iterrows():
        smi  = row[smiles_col].strip() if smiles_col else ""
        name = row[name_col].strip()   if name_col   else ""
        if not smi and not name:
            continue
        rows.append(MoleculeRow(
            row_index=int(i) + 2,          # +2 = 1 for header + 1-based indexing
            smiles=smi      or None,
            iupac_name=name or None if not smi else None,
            label=name or smi,
            raw=row.to_dict(),
        ))
    logger.info("read_excel_file: %d rows parsed from %s", len(rows), path)
    return rows


def read_input_file(path: str, sheet_name: Union[int, str] = 0) -> List[MoleculeRow]:
    """
    Dispatch to the correct reader based on file extension.

    Supported: .csv, .txt, .xlsx, .xls

    Raises:
        ValueError: for unsupported file types.
    """
    suffix = Path(path).suffix.lower()
    dispatch = {
        ".csv":  lambda p: read_csv_file(p),
        ".txt":  lambda p: read_txt_file(p),
        ".xlsx": lambda p: read_excel_file(p, sheet_name=sheet_name),
        ".xls":  lambda p: read_excel_file(p, sheet_name=sheet_name),
    }
    if suffix not in dispatch:
        raise ValueError(
            f"Unsupported file type: {suffix!r}\n"
            f"Supported extensions: {list(dispatch.keys())}"
        )
    rows = dispatch[suffix](path)
    logger.info("read_input_file: %d total rows from %s", len(rows), path)
    return rows


# ── Core Processing ───────────────────────────────────────────────────────────

def _process_one(row: MoleculeRow) -> ProcessedEntry:
    """
    Process a single MoleculeRow: parse → compute descriptors → return ProcessedEntry.

    This function is designed to be safe for multiprocessing (picklable args/returns).
    sys.path manipulation ensures it works when spawned as a subprocess.

    All exceptions are caught and returned as status="error" entries — they
    never propagate to the batch runner.
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from core.molecule_utils   import load_molecule
    from core.descriptor_utils import compute_descriptors

    input_repr = row.smiles or row.iupac_name or f"row_{row.row_index}"

    try:
        mol_rec  = load_molecule(smiles=row.smiles, iupac_name=row.iupac_name)
        if row.label and not mol_rec.name:
            mol_rec.name = row.label

        desc_rec = compute_descriptors(mol_rec.rdkit_mol, mw=mol_rec.mol_weight)

        # FIX-1: inline heterocycle counting directly on rdkit_mol
        # (avoids the non-existent get_heterocycles(desc_rec) import)
        hetero_count = _count_heterocyclic_rings(mol_rec.rdkit_mol)

        return ProcessedEntry(
            row_index=row.row_index,
            input_repr=input_repr,
            status="ok",
            name=mol_rec.name,
            smiles=mol_rec.smiles,
            formula=mol_rec.formula,
            inchikey=mol_rec.inchikey,
            mol_weight=mol_rec.mol_weight,
            exact_mass=mol_rec.exact_mass,
            num_atoms=mol_rec.num_atoms,
            num_heavy_atoms=mol_rec.num_heavy_atoms,
            num_rings=mol_rec.num_rings,
            is_aromatic=mol_rec.is_aromatic,
            logp=desc_rec.logp,
            tpsa=desc_rec.tpsa,
            hbd=desc_rec.hbd,
            hba=desc_rec.hba,
            rotatable_bonds=desc_rec.rotatable_bonds,
            bertz_ct=desc_rec.bertz_ct,
            ro5_pass=desc_rec.ro5_pass,
            ro5_violations=desc_rec.ro5_violations,
            functional_groups=(
                json.dumps(desc_rec.functional_groups)
                if desc_rec.functional_groups else "{}"
            ),
            heterocycles_detected=hetero_count,
        )

    except Exception as exc:
        logger.warning(
            "Row %d skipped [%s]: %s", row.row_index, input_repr[:60], exc
        )
        return ProcessedEntry(
            row_index=row.row_index,
            input_repr=input_repr,
            status="error",
            error=str(exc),
        )


# ── Batch Runner ──────────────────────────────────────────────────────────────

def run_batch(
    rows:           List[MoleculeRow],
    max_workers:    int   = 1,
    rate_limit_s:   float = 0.2,
    progress_every: int   = 10,
) -> BatchResult:
    """
    Execute batch processing over a list of MoleculeRow objects.

    Args:
        rows:           Input rows from any file reader.
        max_workers:    Worker processes (1 = serial, >1 = multiprocessing).
        rate_limit_s:   Seconds to sleep between IUPAC-only rows (PubChem rate limit).
                        Applied only when row.iupac_name is set and row.smiles is None.
        progress_every: Log a progress message every N molecules.

    Returns:
        BatchResult with .df_success, .df_errors, and .summary().

    Notes:
        - Multiprocessing path restores original row_index ordering after futures.
        - rate_limit_s is ignored in multiprocessing mode (caller manages throttle).
    """
    t_start = time.perf_counter()
    entries: List[ProcessedEntry] = []
    total   = len(rows)

    if total == 0:
        logger.warning("run_batch: received 0 rows.")
        return _build_result([], t_start)

    logger.info("Batch start: %d molecules  workers=%d", total, max_workers)

    if max_workers > 1:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_map = {executor.submit(_process_one, row): row for row in rows}
            done = 0
            for future in as_completed(future_map):
                entries.append(future.result())
                done += 1
                if done % progress_every == 0 or done == total:
                    ok = sum(1 for e in entries if e.status == "ok")
                    logger.info("Progress: %d/%d  ok=%d", done, total, ok)
        # FIX-4: restore deterministic input order after concurrent completion
        entries.sort(key=lambda e: e.row_index)
    else:
        for i, row in enumerate(rows, 1):
            # FIX-5: rate-limit only pure IUPAC rows (not SMILES rows)
            if row.iupac_name and not row.smiles and rate_limit_s > 0:
                time.sleep(rate_limit_s)
            entries.append(_process_one(row))
            if i % progress_every == 0 or i == total:
                ok = sum(1 for e in entries if e.status == "ok")
                logger.info("Progress: %d/%d  ok=%d", i, total, ok)

    result = _build_result(entries, t_start)
    logger.info(
        "Batch done: %d/%d ok  %d errors  %.3fs",
        result.n_success, result.total, result.n_errors, result.elapsed_s,
    )
    return result


def _build_result(entries: List[ProcessedEntry], t_start: float) -> BatchResult:
    """Assemble BatchResult from raw entries; strips internal fields from df_success."""
    success = [e for e in entries if e.status == "ok"]
    errors  = [e for e in entries if e.status == "error"]

    # FIX-2: drop status/error columns — they don't belong in the output DataFrame
    df_success = (
        pd.DataFrame([asdict(e) for e in success])
          .drop(columns=["status", "error"], errors="ignore")
        if success else pd.DataFrame()
    )
    df_errors = (
        pd.DataFrame([{
            "row_index":  e.row_index,
            "input_repr": e.input_repr,
            "error":      e.error,
        } for e in errors])
        if errors else pd.DataFrame()
    )

    return BatchResult(
        entries=entries,
        df_success=df_success,
        df_errors=df_errors,
        total=len(entries),
        n_success=len(success),
        n_errors=len(errors),
        elapsed_s=round(time.perf_counter() - t_start, 3),
    )


# ── Public API ────────────────────────────────────────────────────────────────

def process_file(
    path:           str,
    max_workers:    int             = 1,
    rate_limit_s:   float           = 0.2,
    progress_every: int             = 10,
    sheet_name:     Union[int, str] = 0,
) -> BatchResult:
    """
    End-to-end pipeline: read file → process all rows → return BatchResult.

    Supported formats: .csv, .txt, .xlsx, .xls

    Example::

        from core.batch_processor import process_file

        result = process_file("nsc_drugs.csv")
        print(result.summary())
        result.df_success.to_csv("output/results.csv", index=False)
        if not result.df_errors.empty:
            result.df_errors.to_csv("output/errors.csv", index=False)
    """
    rows = read_input_file(path, sheet_name=sheet_name)
    return run_batch(
        rows,
        max_workers=max_workers,
        rate_limit_s=rate_limit_s,
        progress_every=progress_every,
    )


def rows_from_smiles_list(
    smiles_list: List[str],
    names:       Optional[List[str]] = None,
) -> List[MoleculeRow]:
    """
    Convenience constructor: build MoleculeRow objects from a Python list.

    Args:
        smiles_list: SMILES strings (one per molecule).
        names:       Optional parallel list of names/labels.

    Example::

        rows = rows_from_smiles_list(
            ["c1ccccc1", "CC(=O)Oc1ccccc1C(=O)O"],
            names=["Benzene", "Aspirin"],
        )
        result = run_batch(rows)
    """
    if names is not None and len(names) != len(smiles_list):
        raise ValueError(
            f"names has {len(names)} items but smiles_list has {len(smiles_list)}."
        )
    return [
        MoleculeRow(
            row_index=i + 1,
            smiles=smi,
            label=names[i] if names else None,
            raw={"smiles": smi},
        )
        for i, smi in enumerate(smiles_list)
    ]


def convert_file_format(
    input_path: str,
    output_format: str,
    output_dir: str | None = None,
    input_format: str | None = None,
) -> str:
    """Convert a file from one molecular format to another using Open Babel."""
    from core.openbabel_utils import convert_format

    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(input_path)

    input_format = input_format or path.suffix.lower().lstrip(".")
    if not input_format:
        raise ValueError("Could not infer input format from path. Provide input_format.")

    output_path = Path(output_dir) if output_dir else path.parent
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / f"{path.stem}.{output_format.lower()}"

    content = path.read_text(encoding="utf-8", errors="replace")
    converted = convert_format(content, input_format, output_format)
    output_file.write_text(converted, encoding="utf-8")
    return str(output_file)


# ── Example / Smoke Test ──────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    TEST_SMILES = [
        "c1ccccc1",                                  # Benzene
        "CC(=O)Oc1ccccc1C(=O)O",                    # Aspirin
        "Cn1cnc2c1c(=O)n(c(=O)n2C)C",              # Caffeine
        "CC(C)Cc1ccc(cc1)[C@@H](C)C(=O)O",         # Ibuprofen
        "CC(=O)Nc1ccc(O)cc1",                       # Paracetamol
        "INVALID_SMILES_###",                        # Error row
        "CC1(C)SC2C(NC(=O)Cc3ccccc3)C(=O)N2C1C(=O)O",  # Penicillin G
    ]
    TEST_NAMES = ["Benzene","Aspirin","Caffeine","Ibuprofen",
                  "Paracetamol","BAD","Penicillin G"]

    rows   = rows_from_smiles_list(TEST_SMILES, names=TEST_NAMES)
    result = run_batch(rows, max_workers=1, rate_limit_s=0.0)

    print("\n── Summary ──────────────────────────────────────")
    for k, v in result.summary().items():
        print(f"  {k}: {v}")

    print("\n── Successful entries ───────────────────────────")
    cols = ["name","formula","mol_weight","logp","tpsa","ro5_pass","heterocycles_detected"]
    print(result.df_success[cols].to_string(index=False))

    print("\n── Errors ───────────────────────────────────────")
    print(result.df_errors.to_string(index=False))
