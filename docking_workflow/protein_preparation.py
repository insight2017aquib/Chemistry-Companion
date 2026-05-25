import subprocess
import os
import tempfile
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

_FLEX_RECEPTOR_TAGS = {"ROOT", "ENDROOT", "BRANCH", "ENDBRANCH", "TORSDOF"}
_WATER_RESIDUES = {"HOH", "WAT", "H2O"}


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


def prepare_protein(pdb_text: str, remove_water: bool = True, add_charges: bool = True) -> str:
    """
    Cleans protein PDB and outputs PDBQT using obabel, ensuring a clean rigid receptor
    without any ROOT, ENDROOT, BRANCH, ENDBRANCH, or TORSDOF tags.
    """
    logger.info("Starting protein preparation from PDB text.")
    
    if not pdb_text or not pdb_text.strip():
        raise ValueError("Protein PDB text cannot be empty.")

    with tempfile.NamedTemporaryFile(suffix=".pdb", delete=False, mode="w", encoding="utf-8") as tmp_in:
        tmp_in.write(_remove_water_records(pdb_text) if remove_water else pdb_text)
        tmp_in_path = tmp_in.name
        
    tmp_out_path = tmp_in_path + "qt"
    
    try:
        # Build obabel command
        cmd = ["obabel", "-ipdb", tmp_in_path, "-opdbqt", "-O", tmp_out_path, "-xr"]
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
                "Please make sure OpenBabel is installed and added to your system PATH. "
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
