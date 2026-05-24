from dataclasses import dataclass
import subprocess
import tempfile
import os
import logging
import shutil

from .protein_preparation import clean_rigid_receptor_pdbqt

logger = logging.getLogger(__name__)

@dataclass
class VinaResult:
    pdbqt_output: str
    log_text: str


def _resolve_vina_binary() -> str:
    configured = os.getenv("VINA_BINARY") or os.getenv("VINA_EXE")
    candidates = [configured, "vina", "vina.exe"]

    for candidate in candidates:
        if not candidate:
            continue
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
        if os.path.exists(candidate):
            return candidate

    raise RuntimeError(
        "AutoDock Vina executable was not found. Install vina and ensure 'vina' "
        "is on PATH, or set VINA_BINARY to the executable path."
    )


def _validate_pdbqt_input(label: str, pdbqt_text: str) -> None:
    if not pdbqt_text or not pdbqt_text.strip():
        raise ValueError(f"{label} PDBQT text cannot be empty.")

    if not any(line.startswith(("ATOM", "HETATM")) for line in pdbqt_text.splitlines()):
        raise ValueError(f"{label} PDBQT does not contain any ATOM/HETATM records.")


def _validate_box_dimension(name: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero.")

def run_vina(
    protein_pdbqt: str,
    ligand_pdbqt: str,
    center_x: float,
    center_y: float,
    center_z: float,
    size_x: float,
    size_y: float,
    size_z: float,
    exhaustiveness: int = 8,
    num_modes: int = 9,
    timeout: int = 300
) -> VinaResult:
    """
    Invokes vina.exe via subprocess to dock ligand to protein.
    """
    protein_pdbqt, removed_tags = clean_rigid_receptor_pdbqt(protein_pdbqt)
    if removed_tags:
        logger.warning("Removed receptor torsion-tree tags before Vina run: %s", sorted(set(removed_tags)))

    _validate_pdbqt_input("Receptor", protein_pdbqt)
    _validate_pdbqt_input("Ligand", ligand_pdbqt)
    for name, value in {
        "size_x": size_x,
        "size_y": size_y,
        "size_z": size_z,
        "exhaustiveness": exhaustiveness,
        "num_modes": num_modes,
    }.items():
        _validate_box_dimension(name, value)

    vina_binary = _resolve_vina_binary()
    tmp_prot = tempfile.NamedTemporaryFile(suffix=".pdbqt", delete=False, mode="w", encoding="utf-8")
    tmp_lig = tempfile.NamedTemporaryFile(suffix=".pdbqt", delete=False, mode="w", encoding="utf-8")
    tmp_out_fd, tmp_out_path = tempfile.mkstemp(suffix=".pdbqt")
    os.close(tmp_out_fd)
    os.remove(tmp_out_path)
    
    try:
        tmp_prot.write(protein_pdbqt)
        tmp_prot.close()
        
        tmp_lig.write(ligand_pdbqt)
        tmp_lig.close()
        
        cmd = [
            vina_binary,
            "--receptor", tmp_prot.name,
            "--ligand", tmp_lig.name,
            "--center_x", str(center_x),
            "--center_y", str(center_y),
            "--center_z", str(center_z),
            "--size_x", str(size_x),
            "--size_y", str(size_y),
            "--size_z", str(size_z),
            "--out", tmp_out_path,
            "--exhaustiveness", str(exhaustiveness),
            "--num_modes", str(num_modes),
        ]
        
        logger.info(
            "Running Vina docking: center=(%.3f, %.3f, %.3f), size=(%.3f, %.3f, %.3f), "
            "exhaustiveness=%s, num_modes=%s",
            center_x, center_y, center_z, size_x, size_y, size_z, exhaustiveness, num_modes
        )
        logger.debug("Vina command: %s", " ".join(cmd))

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        log_text = "\n".join(part for part in (result.stdout, result.stderr) if part)
        
        if result.returncode != 0:
            logger.error("Vina failed with exit code %s. Output: %s", result.returncode, log_text)
            raise RuntimeError(f"Vina failed with exit code {result.returncode}: {log_text or 'No output'}")

        if not os.path.exists(tmp_out_path):
            raise RuntimeError(f"Vina completed but did not create output file. Log: {log_text or 'No output'}")
            
        with open(tmp_out_path, "r", encoding="utf-8") as f:
            out_pdbqt = f.read()

        if not out_pdbqt.strip():
            raise RuntimeError(f"Vina completed but produced an empty output file. Log: {log_text or 'No output'}")

        logger.info("Vina docking completed successfully. Output length: %d bytes.", len(out_pdbqt))
        return VinaResult(pdbqt_output=out_pdbqt, log_text=log_text)
        
    except subprocess.TimeoutExpired:
        logger.error(f"Vina docking timed out after {timeout} seconds.")
        raise RuntimeError(f"Docking timed out after {timeout} seconds.")
    finally:
        for handle in (tmp_prot, tmp_lig):
            try:
                handle.close()
            except Exception:
                pass
        for fpath in [tmp_prot.name, tmp_lig.name, tmp_out_path]:
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except OSError:
                    logger.debug("Could not remove temporary docking file: %s", fpath)
