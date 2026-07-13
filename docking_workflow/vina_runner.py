from dataclasses import dataclass
import subprocess
import tempfile
import os
import logging
import shutil
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dotenv is optional at import time
    load_dotenv = None

from .protein_preparation import clean_rigid_receptor_pdbqt

logger = logging.getLogger(__name__)

if load_dotenv is not None:
    load_dotenv()

@dataclass
class VinaResult:
    pdbqt_output: str
    log_text: str


def _clean_binary_path(value: str | None) -> str | None:
    if not value:
        return None
    return os.path.expandvars(os.path.expanduser(value.strip().strip('"').strip("'")))


def _local_vina_candidates() -> list[str]:
    root = Path(__file__).resolve().parents[1]
    executable_dir = Path(sys.executable).resolve().parent
    names = ("vina", "vina.exe")
    candidates: list[str] = []
    for base in (executable_dir, root / ".venv" / "Scripts"):
        for name in names:
            candidates.append(str(base / name))

    # Extra Windows/conda + pip 'vina' package locations (stabilization)
    # Covers common cases where native CLI binary ends up in Library/bin or
    # vendored inside the pypi 'vina' package tree or user caches.
    try:
        conda_prefix = Path(sys.prefix)
        candidates.append(str(conda_prefix / "Library" / "bin" / "vina.exe"))
        candidates.append(str(conda_prefix / "Library" / "bin" / "vina"))
    except Exception:
        pass

    try:
        import vina as _vina_pkg  # pypi 'vina' package may vendor or download the CLI
        vroot = Path(_vina_pkg.__file__).resolve().parent
        for name in names:
            candidates.append(str(vroot / name))
            candidates.append(str(vroot / "bin" / name))
        for p in vroot.rglob("vina*"):
            if p.is_file() and p.suffix in ("", ".exe"):
                candidates.append(str(p))
    except Exception:
        pass

    # Common user cache locations used by autodock tools / pypi vina on first run
    home = Path.home()
    for cand in (
        home / ".vina" / "vina.exe",
        home / ".vina" / "vina",
        home / "AppData" / "Local" / "vina" / "vina.exe",
    ):
        candidates.append(str(cand))

    return candidates


def _resolve_vina_binary() -> str:
    configured = _clean_binary_path(os.getenv("VINA_BINARY") or os.getenv("VINA_EXE"))
    local_cands = _local_vina_candidates()
    candidates = [configured, "vina", "vina.exe", *local_cands]

    tried = []
    for candidate in candidates:
        if not candidate:
            continue
        tried.append(candidate)
        resolved = shutil.which(candidate)
        if resolved:
            logger.info("Resolved Vina binary via which: %s", resolved)
            return resolved
        if os.path.exists(candidate):
            logger.info("Resolved Vina binary via direct path: %s", candidate)
            return candidate

    # Helpful diagnostics for common Windows/conda/pip-vina mixes
    detail = "Tried candidates (in order): " + "; ".join(tried[:12]) + (" ..." if len(tried) > 12 else "")
    raise RuntimeError(
        "AutoDock Vina executable (the native CLI 'vina'/'vina.exe') was not found.\n"
        f"{detail}\n\n"
        "Common fixes (do not mix pip 'vina' package with the CLI):\n"
        "  Preferred: conda install -c conda-forge vina\n"
        "  Then ensure the env's Scripts or Library/bin is on PATH when running the server.\n"
        "  Alternative: download the official vina binary for Windows and set VINA_BINARY=\"C:\\full\\path\\to\\vina.exe\"\n"
        "  (or add it to a .env file at project root; dotenv is loaded automatically).\n"
        "Note: the PyPI 'vina' package provides a Python API but usually does not install the standalone CLI binary that this docking engine invokes via subprocess."
    )


def _parse_score_only(text: str) -> float | None:
    """Extract the binding affinity (kcal/mol) from Vina --score_only output."""
    if not text:
        return None
    import re
    # Vina 1.2: "Estimated Free Energy of Binding   : -7.34 (kcal/mol)"
    m = re.search(r"Estimated Free Energy of Binding\s*[:=]\s*(-?\d+\.?\d*)", text)
    if m:
        return float(m.group(1))
    # Older/alt formats: "Affinity: -7.34 (kcal/mol)"
    m = re.search(r"Affinity:\s*(-?\d+\.?\d*)", text)
    if m:
        return float(m.group(1))
    return None


def rescore_pose(
    protein_pdbqt: str,
    pose_pdbqt: str,
    center_x: float,
    center_y: float,
    center_z: float,
    size_x: float,
    size_y: float,
    size_z: float,
    scoring_function: str = "vinardo",
    timeout: int = 120,
) -> float | None:
    """Re-score an existing pose with a (possibly different) scoring function using
    Vina's ``--score_only`` mode. Returns the affinity in kcal/mol, or None if the
    standalone CLI is unavailable or scoring failed (graceful — never raises).

    This is the workhorse behind consensus scoring: dock with ``vina``, then re-score
    the top poses with ``vinardo`` (or vice-versa) for an independent second opinion.
    """
    protein_pdbqt, _ = clean_rigid_receptor_pdbqt(protein_pdbqt)
    scoring_function = (scoring_function or "vina").strip().lower()
    if scoring_function not in _VALID_SCORING_FUNCTIONS:
        raise ValueError(f"Unsupported scoring function: {scoring_function}.")

    try:
        vina_binary = _resolve_vina_binary()
    except RuntimeError:
        logger.info("Rescoring skipped: standalone Vina CLI not available.")
        return None

    tmp_prot = tempfile.NamedTemporaryFile(suffix=".pdbqt", delete=False, mode="w", encoding="utf-8")
    tmp_lig = tempfile.NamedTemporaryFile(suffix=".pdbqt", delete=False, mode="w", encoding="utf-8")
    try:
        tmp_prot.write(protein_pdbqt); tmp_prot.close()
        tmp_lig.write(pose_pdbqt); tmp_lig.close()
        cmd = [
            vina_binary,
            "--receptor", tmp_prot.name,
            "--ligand", tmp_lig.name,
            "--center_x", str(center_x), "--center_y", str(center_y), "--center_z", str(center_z),
            "--size_x", str(size_x), "--size_y", str(size_y), "--size_z", str(size_z),
            "--scoring", scoring_function,
            "--score_only",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        affinity = _parse_score_only("\n".join(p for p in (result.stdout, result.stderr) if p))
        if affinity is None:
            logger.warning("Rescoring produced no parseable affinity (scoring=%s).", scoring_function)
        return affinity
    except subprocess.TimeoutExpired:
        logger.warning("Rescoring timed out after %ss.", timeout)
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Rescoring failed: %s", exc)
        return None
    finally:
        for fpath in (tmp_prot.name, tmp_lig.name):
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except OSError:
                    pass


def _get_python_vina_instance(scoring_function: str = "vina", seed: int | None = None):
    """Attempt to get a working vina.Vina instance from the pypi package (fallback when no CLI)."""
    try:
        import vina
        kwargs = {"sf_name": scoring_function}
        if seed is not None:
            kwargs["seed"] = seed
        # This will download the binary on first use if missing
        v = vina.Vina(**kwargs)
        return v
    except Exception as e:
        logger.debug("Python vina package not usable: %s", e)
        return None


def _validate_pdbqt_input(label: str, pdbqt_text: str) -> None:
    if not pdbqt_text or not pdbqt_text.strip():
        raise ValueError(f"{label} PDBQT text cannot be empty.")

    if not any(line.startswith(("ATOM", "HETATM")) for line in pdbqt_text.splitlines()):
        raise ValueError(f"{label} PDBQT does not contain any ATOM/HETATM records.")


def _validate_box_dimension(name: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero.")

_VALID_SCORING_FUNCTIONS = {"vina", "vinardo", "ad4"}


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
    timeout: int = 300,
    scoring_function: str = "vina",
    seed: int | None = None,
    flex_pdbqt: str | None = None,
) -> VinaResult:
    """
    Invokes vina.exe via subprocess to dock ligand to protein.

    If ``flex_pdbqt`` is provided (a receptor-flexible-sidechain PDBQT produced by
    prepare_flexible_receptor), it is passed to Vina via ``--flex`` for flexible
    side-chain docking. Flexible docking requires the standalone CLI; it is ignored
    on the Python-package fallback path.
    """
    logger.info("run_vina ENTRY: about to resolve binary and execute for receptor_len=%d ligand_len=%d", len(protein_pdbqt or ''), len(ligand_pdbqt or ''))
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

    scoring_function = (scoring_function or "vina").strip().lower()
    if scoring_function not in _VALID_SCORING_FUNCTIONS:
        raise ValueError(f"Unsupported scoring function: {scoring_function}. Choose one of {sorted(_VALID_SCORING_FUNCTIONS)}.")

    # Try CLI first (preferred for this architecture)
    try:
        vina_binary = _resolve_vina_binary()
        use_cli = True
    except RuntimeError:
        # Fallback to Python 'vina' package if available (makes real docking work
        # in environments that only have the pip package)
        python_vina = _get_python_vina_instance(scoring_function, seed)
        if python_vina is None:
            raise
        use_cli = False
        logger.warning("No standalone Vina CLI found. Falling back to Python 'vina' package API for real docking.")

    if use_cli:
        tmp_prot = tempfile.NamedTemporaryFile(suffix=".pdbqt", delete=False, mode="w", encoding="utf-8")
        tmp_lig = tempfile.NamedTemporaryFile(suffix=".pdbqt", delete=False, mode="w", encoding="utf-8")
        tmp_flex = None
        if flex_pdbqt and flex_pdbqt.strip():
            tmp_flex = tempfile.NamedTemporaryFile(suffix=".pdbqt", delete=False, mode="w", encoding="utf-8")
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
                "--scoring", scoring_function,
            ]
            if tmp_flex is not None:
                tmp_flex.write(flex_pdbqt)
                tmp_flex.close()
                cmd.extend(["--flex", tmp_flex.name])
                logger.info("Flexible receptor docking enabled (flex sidechains provided).")
            if seed is not None:
                cmd.extend(["--seed", str(seed)])

            logger.info(
                "Running Vina docking: center=(%.3f, %.3f, %.3f), size=(%.3f, %.3f, %.3f), "
                "exhaustiveness=%s, num_modes=%s, scoring=%s, seed=%s",
                center_x, center_y, center_z, size_x, size_y, size_z, exhaustiveness, num_modes,
                scoring_function, seed
            )
            logger.debug("Vina command: %s", " ".join(cmd))
            logger.info("EXECUTING Vina subprocess now (timeout=%ss)", timeout)

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
            handles = [tmp_prot, tmp_lig] + ([tmp_flex] if tmp_flex is not None else [])
            for handle in handles:
                try:
                    handle.close()
                except Exception:
                    pass
            cleanup_paths = [tmp_prot.name, tmp_lig.name, tmp_out_path]
            if tmp_flex is not None:
                cleanup_paths.append(tmp_flex.name)
            for fpath in cleanup_paths:
                if os.path.exists(fpath):
                    try:
                        os.remove(fpath)
                    except OSError:
                        logger.debug("Could not remove temporary docking file: %s", fpath)
    else:
        # Python vina package fallback path (real docking using the available API)
        python_vina = _get_python_vina_instance(scoring_function, seed)
        if python_vina is None:
            raise RuntimeError("Neither CLI nor Python vina package available for docking.")

        tmp_prot = tempfile.NamedTemporaryFile(suffix=".pdbqt", delete=False, mode="w", encoding="utf-8")
        tmp_lig = tempfile.NamedTemporaryFile(suffix=".pdbqt", delete=False, mode="w", encoding="utf-8")
        tmp_out_path = tmp_prot.name + "_out.pdbqt"

        try:
            tmp_prot.write(protein_pdbqt)
            tmp_prot.close()
            tmp_lig.write(ligand_pdbqt)
            tmp_lig.close()

            python_vina.set_receptor(tmp_prot.name)
            python_vina.set_ligand_from_file(tmp_lig.name)
            python_vina.compute_vina_maps(center=[center_x, center_y, center_z], box_size=[size_x, size_y, size_z])
            logger.info("EXECUTING Vina via python package API now (exh=%s, n=%s)", exhaustiveness, num_modes)
            python_vina.dock(exhaustiveness=exhaustiveness, n_poses=num_modes)
            python_vina.write_poses(tmp_out_path)

            with open(tmp_out_path, "r", encoding="utf-8") as f:
                out_pdbqt = f.read()

            log_text = f"Python vina package docking completed. Exhaustiveness={exhaustiveness}, n_poses={num_modes}"

            logger.info("Real Vina docking completed via Python package fallback. Output length: %d bytes.", len(out_pdbqt))
            return VinaResult(pdbqt_output=out_pdbqt, log_text=log_text)
        finally:
            for fpath in [tmp_prot.name, tmp_lig.name, tmp_out_path]:
                if os.path.exists(fpath):
                    try:
                        os.remove(fpath)
                    except Exception:
                        pass
