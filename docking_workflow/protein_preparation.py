import subprocess
import os
import shutil
import sys
import tempfile
import logging
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

_FLEX_RECEPTOR_TAGS = {"ROOT", "ENDROOT", "BRANCH", "ENDBRANCH", "TORSDOF"}
_WATER_RESIDUES = {"HOH", "WAT", "H2O", "WTR"}


def _clean_binary_path(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return os.path.expandvars(os.path.expanduser(value.strip().strip('"').strip("'")))


def _resolve_obabel_binary() -> str:
    """Locate the OpenBabel CLI ('obabel').

    Running the server with the venv interpreter directly (``.venv/Scripts/python.exe``)
    does NOT put ``.venv/Scripts`` on PATH, so a bare ``obabel`` call fails with
    WinError 2 even though obabel is installed in the venv. This resolver mirrors the
    Vina binary resolver: honor OBABEL_BINARY/OBABEL_EXE, then look next to the running
    interpreter, the project venv, and conda's Library/bin, then fall back to PATH.
    """
    configured = _clean_binary_path(os.getenv("OBABEL_BINARY") or os.getenv("OBABEL_EXE"))
    names = ("obabel", "obabel.exe")

    candidates: List[str] = [configured] if configured else []
    root = Path(__file__).resolve().parents[1]
    exe_dir = Path(sys.executable).resolve().parent
    for base in (exe_dir, root / ".venv" / "Scripts"):
        for name in names:
            candidates.append(str(base / name))
    try:
        conda_prefix = Path(sys.prefix)
        for name in names:
            candidates.append(str(conda_prefix / "Library" / "bin" / name))
    except Exception:
        pass
    candidates.extend(names)  # finally, trust PATH

    for cand in candidates:
        if not cand:
            continue
        resolved = shutil.which(cand)
        if resolved:
            return resolved
        if os.path.exists(cand):
            return cand
    # Nothing found — return the bare name so the caller's FileNotFoundError handler
    # produces its helpful install message.
    return "obabel"


def _remove_water_records(pdb_text: str) -> str:
    cleaned_lines = []
    removed_count = 0

    for line in pdb_text.splitlines():
        if line.startswith(("ATOM", "HETATM")) and line[17:20].strip().upper() in _WATER_RESIDUES:
            removed_count += 1
            continue
        cleaned_lines.append(line)

    if removed_count:
        logger.info("Removed %d water atom records before receptor preparation.", removed_count)

    return "\n".join(cleaned_lines) + "\n"


def _remove_ligand_records(pdb_text: str) -> str:
    """
    Remove co-crystallized small-molecule ligand HETATM records from a PDB.

    A docking receptor must NOT contain the bound ligand — otherwise the pocket is
    occupied and docking is meaningless. Only records classified as *ligand* (via the
    shared _classify_hetatm logic) are dropped; waters, metals, and cofactors are left
    untouched here (they are handled by their own retention logic / water removal).
    """
    from .protein_analysis import _classify_hetatm

    cleaned_lines = []
    removed_count = 0
    for line in pdb_text.splitlines():
        if line.startswith("HETATM"):
            resname = line[17:20].strip().upper()
            kind, _classification, _status = _classify_hetatm(resname)
            if kind == "ligand":
                removed_count += 1
                continue
        cleaned_lines.append(line)

    if removed_count:
        logger.info("Removed %d co-crystal ligand atom records before receptor preparation.", removed_count)

    return "\n".join(cleaned_lines) + "\n"


def _split_pdbqt_token(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return ""
    return stripped.split(maxsplit=1)[0].upper()


def clean_rigid_receptor_pdbqt(pdbqt_text: str) -> Tuple[str, List[str]]:
    """
    Remove flexible-ligand torsion-tree tags from receptor PDBQT text.

    AutoDock Vina rigid receptors must be plain receptor PDBQT files. If OpenBabel
    emits ligand-style ROOT/BRANCH/TORSDOF records, Vina rejects the receptor.
    """
    cleaned_lines = []
    removed_tags = []

    for line in pdbqt_text.splitlines():
        token = _split_pdbqt_token(line)
        if token in _FLEX_RECEPTOR_TAGS:
            removed_tags.append(line.strip())
            continue
        cleaned_lines.append(line.rstrip())

    cleaned_pdbqt = "\n".join(cleaned_lines).strip()
    if cleaned_pdbqt:
        cleaned_pdbqt += "\n"

    validate_rigid_receptor_pdbqt(cleaned_pdbqt)
    return cleaned_pdbqt, removed_tags


def validate_rigid_receptor_pdbqt(pdbqt_text: str) -> None:
    """
    Validate that receptor PDBQT text is non-empty and contains no torsion-tree tags.
    """
    if not pdbqt_text or not pdbqt_text.strip():
        raise ValueError("Prepared receptor PDBQT is empty.")

    remaining_tags = [
        line.strip()
        for line in pdbqt_text.splitlines()
        if _split_pdbqt_token(line) in _FLEX_RECEPTOR_TAGS
    ]
    if remaining_tags:
        raise ValueError(
            "Rigid receptor PDBQT still contains flexible torsion-tree tags: "
            + ", ".join(sorted(set(remaining_tags)))
        )

    if not any(line.startswith(("ATOM", "HETATM")) for line in pdbqt_text.splitlines()):
        raise ValueError("Prepared receptor PDBQT does not contain any ATOM/HETATM records.")


def prepare_protein(
    pdb_text: str,
    remove_water: bool = True,
    add_charges: bool = True,
    remove_ligands: bool = True,
) -> str:
    """
    Cleans protein PDB and outputs PDBQT using obabel, ensuring a clean rigid receptor
    without any ROOT, ENDROOT, BRANCH, ENDBRANCH, or TORSDOF tags.

    By default the co-crystallized ligand is stripped (remove_ligands=True) so the
    docking pocket is empty. Callers that have already filtered HETATM records
    (e.g. prepare_receptor via _classify_and_filter_pdb) pass remove_ligands=False
    to avoid double-processing.
    """
    logger.info("Starting protein preparation from PDB text.")

    if not pdb_text or not pdb_text.strip():
        raise ValueError("Protein PDB text cannot be empty.")

    prepared_input = _remove_water_records(pdb_text) if remove_water else pdb_text
    if remove_ligands:
        prepared_input = _remove_ligand_records(prepared_input)

    with tempfile.NamedTemporaryFile(suffix=".pdb", delete=False, mode="w", encoding="utf-8") as tmp_in:
        tmp_in.write(prepared_input)
        tmp_in_path = tmp_in.name
        
    tmp_out_path = tmp_in_path + "qt"
    
    try:
        # Build obabel command (resolve the binary so it works even when the server
        # runs with the venv interpreter but .venv/Scripts is not on PATH).
        obabel_binary = _resolve_obabel_binary()
        cmd = [obabel_binary, "-ipdb", tmp_in_path, "-opdbqt", "-O", tmp_out_path, "-xr"]
        if add_charges:
            cmd.extend(["-p", "7.4"])
        
        logger.debug(f"Running OpenBabel command: {' '.join(cmd)}")
        
        # Run obabel
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        except FileNotFoundError:
            logger.error("obabel executable not found in system PATH.")
            raise RuntimeError(
                "OpenBabel executable ('obabel') was not found. "
                "Please make sure OpenBabel is installed and on PATH, set OBABEL_BINARY to its "
                "full path, or run the server from an activated environment. "
                "You can install it in Conda via: conda install -c conda-forge openbabel"
            )
            
        if not os.path.exists(tmp_out_path):
            raise RuntimeError(f"OpenBabel completed but no output file was created at {tmp_out_path}. Stderr: {result.stderr}")
            
        with open(tmp_out_path, "r", encoding="utf-8") as f:
            pdbqt_text = f.read()
            
        # Post-process the PDBQT to strictly guarantee a clean rigid receptor
        # Rigid receptors in AutoDock Vina MUST NOT contain any flex tags like ROOT, ENDROOT, TORSDOF, etc.
        cleaned_pdbqt, removed_tags = clean_rigid_receptor_pdbqt(pdbqt_text)
            
        if removed_tags:
            logger.info(f"Cleaned rigid receptor PDBQT. Removed tags: {', '.join(set(removed_tags))}")
        else:
            logger.info("Rigid receptor PDBQT was already clean.")
            
        return cleaned_pdbqt
        
    except subprocess.CalledProcessError as e:
        logger.error(f"OpenBabel failed with exit code {e.returncode}. Stderr: {e.stderr}")
        raise RuntimeError(
            f"OpenBabel preparation failed: {e.stderr or e.stdout or 'Unknown error'}"
        )
    except Exception as e:
        logger.exception("Unexpected error during protein preparation:")
        raise RuntimeError(f"Protein preparation failed: {str(e)}")
    finally:
        if os.path.exists(tmp_in_path):
            try: os.remove(tmp_in_path)
            except Exception: pass
        if os.path.exists(tmp_out_path):
            try: os.remove(tmp_out_path)
            except Exception: pass


# ──────────────────────────────────────────────────────────────────────────────
# Phase 4/5 rich preparation API (added to resolve import failure for callers
# that expect prepare_receptor + PreparationOptions).
# The advanced keep_* flags are accepted for compatibility but the underlying
# preparation engine (obabel + current cleaners) does not yet implement
# selective cofactor/metal/active-site water retention. Protonation is composed
# when requested.
# ──────────────────────────────────────────────────────────────────────────────

from dataclasses import dataclass


@dataclass
class PreparationOptions:
    """Configuration for advanced receptor preparation."""
    remove_water: bool = True
    add_charges: bool = True
    keep_cofactors: bool = False
    keep_metals: bool = False
    keep_active_site_waters: bool = False
    remove_bulk_waters: bool = True
    remove_ligands: bool = True
    run_protonation: bool = False
    ph: float = 7.4


def _classify_and_filter_pdb(
    pdb_text: str,
    *,
    remove_water: bool,
    keep_cofactors: bool,
    keep_metals: bool,
    keep_active_site_waters: bool,
    remove_bulk_waters: bool,
    remove_ligands: bool = True,
) -> Tuple[str, dict]:
    """
    Selectively filter HETATM records (waters, cofactors, metals) based on the
    caller's retention preferences, using the same classification logic the
    pre-docking analysis UI already shows the user (analyze_receptor +
    classify_waters), so what the user sees in the wizard is what gets docked.
    """
    from .protein_analysis import analyze_receptor, _classify_hetatm
    from .water_analysis import classify_waters

    removed = {"water_bulk": 0, "water_active_site": 0, "cofactor": 0, "metal": 0, "ligand": 0}

    active_site_water_keys = set()
    if remove_water:
        try:
            report = analyze_receptor(pdb_text)
            waters = classify_waters(pdb_text, report)
            for w in waters:
                if w.category in ("active_site", "conserved"):
                    active_site_water_keys.add((w.chain_id, w.resnum))
        except Exception as exc:
            logger.warning(
                "Water classification failed during selective filtering (%s); "
                "treating all waters as bulk.", exc
            )

    cleaned_lines = []
    for line in pdb_text.splitlines():
        if line.startswith(("ATOM", "HETATM")):
            resname = line[17:20].strip().upper()

            if resname in _WATER_RESIDUES:
                if not remove_water:
                    cleaned_lines.append(line)
                    continue
                chain_id = line[21:22].strip() or "_"
                try:
                    resnum = int(line[22:26].strip())
                except ValueError:
                    resnum = 0
                is_active_site = (chain_id, resnum) in active_site_water_keys
                if is_active_site:
                    if keep_active_site_waters:
                        cleaned_lines.append(line)
                    else:
                        removed["water_active_site"] += 1
                elif remove_bulk_waters:
                    removed["water_bulk"] += 1
                else:
                    cleaned_lines.append(line)
                continue

            kind, _classification, _status = _classify_hetatm(resname)
            if kind == "cofactor" and not keep_cofactors:
                removed["cofactor"] += 1
                continue
            if kind == "metal" and not keep_metals:
                removed["metal"] += 1
                continue
            # NB: _classify_hetatm returns "ligand" as its catch-all default, which also
            # covers standard amino acids in ATOM records. Only HETATM records may be a
            # co-crystal ligand — restricting to HETATM prevents deleting the protein.
            if kind == "ligand" and remove_ligands and line.startswith("HETATM"):
                # Co-crystallized ligand: must be removed so the docking pocket is empty.
                removed["ligand"] += 1
                continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines) + "\n", removed


def prepare_receptor(pdb_text: str, options: PreparationOptions) -> str:
    """
    Rich entry point expected by DockingWorkspaceService.prepare_receptor_with_options.

    - Applies protonation first if options.run_protonation is True (reuses existing protonation module).
    - Applies selective retention of cofactors/metals/active-site waters per the options,
      using analyze_receptor()/classify_waters() as the source of truth.
    - Delegates the remaining PDB → clean rigid PDBQT work to prepare_protein.
    """
    text = pdb_text or ""
    protonation_applied = False

    if getattr(options, "run_protonation", False):
        try:
            from .protonation import protonate_receptor
            ph = getattr(options, "ph", 7.4)
            text = protonate_receptor(text, ph=ph)
            protonation_applied = True
            logger.info("Applied protonation at pH %.1f before receptor preparation.", ph)
        except Exception as e:
            logger.warning("Protonation requested but failed to apply: %s", e)

    keep_cofactors = getattr(options, "keep_cofactors", False)
    keep_metals = getattr(options, "keep_metals", False)
    keep_active_site_waters = getattr(options, "keep_active_site_waters", False)
    remove_bulk_waters = getattr(options, "remove_bulk_waters", True)
    remove_water = getattr(options, "remove_water", True)
    remove_ligands = getattr(options, "remove_ligands", True)

    filtered_ok = False
    try:
        text, removed = _classify_and_filter_pdb(
            text,
            remove_water=remove_water,
            keep_cofactors=keep_cofactors,
            keep_metals=keep_metals,
            keep_active_site_waters=keep_active_site_waters,
            remove_bulk_waters=remove_bulk_waters,
            remove_ligands=remove_ligands,
        )
        filtered_ok = True
        logger.info(
            "Selective retention applied: removed %d bulk water(s), %d active-site water(s), "
            "%d cofactor atom(s), %d metal atom(s), %d co-crystal ligand atom(s) "
            "(keep_cofactors=%s, keep_metals=%s, keep_active_site_waters=%s, "
            "remove_bulk_waters=%s, remove_ligands=%s).",
            removed["water_bulk"], removed["water_active_site"], removed["cofactor"], removed["metal"],
            removed["ligand"], keep_cofactors, keep_metals, keep_active_site_waters,
            remove_bulk_waters, remove_ligands,
        )
    except Exception as exc:
        logger.warning(
            "Selective retention filtering failed (%s); falling back to blanket water/ligand removal.", exc
        )

    # Water and ligand removal are handled above by the selective filter when it
    # succeeds, so prepare_protein must not repeat them. If the filter failed, let
    # prepare_protein apply its own blanket water + ligand strip as a safe fallback.
    return prepare_protein(
        text,
        remove_water=False if filtered_ok else remove_water,
        add_charges=getattr(options, "add_charges", True) and not protonation_applied,
        remove_ligands=False if filtered_ok else remove_ligands,
    )


def prepare_flexible_receptor(
    receptor_pdbqt: str,
    flex_residues: List[str],
) -> Tuple[str, str]:
    """
    Split a rigid receptor PDBQT into (rigid_pdbqt, flex_pdbqt) for flexible
    side-chain docking with Vina's --flex option.

    ``flex_residues`` is a list of residue identifiers to make flexible, e.g.
    ["A:THR315", "A:PHE382"] or ["THR315", "PHE382"].

    This delegates to Meeko's flexible-receptor writer when available. If Meeko (or
    its receptor tooling) is not installed, it raises RuntimeError with clear guidance
    rather than silently producing an invalid split — flexible docking with a bad
    torsion tree is worse than none.
    """
    if not flex_residues:
        raise ValueError("No flexible residues specified.")

    try:
        from meeko import PDBQTReceptor  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Flexible receptor preparation requires Meeko's receptor tooling "
            "(meeko>=0.5 with PDBQTReceptor). Install/upgrade meeko, or dock rigidly. "
            f"Import error: {exc}"
        )

    try:
        receptor = PDBQTReceptor(receptor_pdbqt)
        rigid_pdbqt, flex_pdbqt = receptor.write_pdbqt_string(flexres=flex_residues)
        if not flex_pdbqt or not flex_pdbqt.strip():
            raise RuntimeError(
                "Meeko produced an empty flexible-residue PDBQT; check that the "
                "requested residue identifiers exist in the receptor."
            )
        # The rigid part must still be a clean rigid receptor.
        rigid_pdbqt, _ = clean_rigid_receptor_pdbqt(rigid_pdbqt)
        logger.info("Prepared flexible receptor: %d flexible residue(s).", len(flex_residues))
        return rigid_pdbqt, flex_pdbqt
    except RuntimeError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Flexible receptor preparation failed: {exc}")
