"""
docking_workflow/redock_validation.py
=====================================
Redocking (cognate-ligand) validation — the "is this protocol trustworthy?" check.

When a receptor ships with a co-crystallized ligand (e.g. PDB 4DUH), the field-standard
way to validate a docking protocol is to:

  1. Remove the native ligand from the receptor,
  2. Re-dock it into the same grid with the same preparation/scoring settings,
  3. Measure the RMSD between the top docked pose and the crystallographic pose.

A protocol that reproduces the crystal pose (RMSD < ~2 Å) can be trusted to rank
analogues; one that cannot should not be believed. This is intentionally separate
from Vina's internal inter-pose RMSDs (rmsd_lb/rmsd_ub in the standard report),
which do NOT measure agreement with the crystal structure.

RMSD is computed alignment-free (both poses live in the same receptor coordinate
frame) and symmetry-tolerant. No fabricated numbers: if RMSD cannot be computed,
the result says so explicitly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Heavy-atom elements we score RMSD on (hydrogens are excluded — their positions
# are prep-dependent and not resolved in most X-ray structures).
_HYDROGEN = {"H", "D"}

# RMSD thresholds (Å) for the pass/fail badge — standard cognate-redocking cutoffs.
RMSD_PASS = 2.0
RMSD_AMBER = 3.0


@dataclass
class RedockValidationResult:
    status: str                       # "pass" | "acceptable" | "fail" | "error"
    rmsd: Optional[float]             # heavy-atom, symmetry-tolerant, alignment-free
    rmsd_method: Optional[str]        # "rdkit" | "hungarian" | None
    reference_resname: Optional[str]
    reference_chain: Optional[str]
    reference_resnum: Optional[int]
    best_affinity: Optional[float]
    grid: Optional[Dict[str, float]]
    num_poses: int = 0
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# PDB / PDBQT atom parsing (heavy atoms only)
# ---------------------------------------------------------------------------

def _element_from_line(line: str) -> str:
    """Best-effort element symbol from a PDB/PDBQT ATOM/HETATM line."""
    # Columns 77-78 hold the element in well-formed PDB; fall back to the atom name.
    elem = line[76:78].strip() if len(line) >= 78 else ""
    if not elem:
        name = line[12:16].strip()
        # Strip leading digits/altloc and take leading alpha chars
        elem = "".join(c for c in name if c.isalpha())[:2]
    elem = elem.strip().capitalize()
    return elem


def _parse_heavy_atoms(block: str) -> List[Tuple[str, float, float, float]]:
    """Return [(element, x, y, z), ...] for heavy atoms in a PDB/PDBQT block."""
    atoms: List[Tuple[str, float, float, float]] = []
    for line in block.splitlines():
        if not line.startswith(("ATOM", "HETATM")):
            continue
        try:
            x = float(line[30:38])
            y = float(line[38:46])
            z = float(line[46:54])
        except (ValueError, IndexError):
            continue
        elem = _element_from_line(line)
        if elem in _HYDROGEN or not elem:
            continue
        atoms.append((elem, x, y, z))
    return atoms


# ---------------------------------------------------------------------------
# Ligand extraction / receptor stripping
# ---------------------------------------------------------------------------

def _residue_key(line: str) -> Tuple[str, str, str]:
    return (
        line[17:20].strip().upper(),   # resname
        line[21:22].strip() or "_",    # chain
        line[22:26].strip(),           # resnum (string, keeps insertion codes out)
    )


def extract_ligand_block(pdb_text: str, resname: str, chain: str, resnum: int) -> str:
    """Return a minimal PDB block containing only the requested ligand residue."""
    want = (resname.strip().upper(), (chain or "_").strip() or "_", str(resnum))
    kept = [
        line for line in pdb_text.splitlines()
        if line.startswith(("ATOM", "HETATM")) and _residue_key(line) == want
    ]
    if not kept:
        raise ValueError(f"Ligand {resname} {chain}:{resnum} not found in structure.")
    return "\n".join(kept) + "\nEND\n"


def strip_residue(pdb_text: str, resname: str, chain: str, resnum: int) -> str:
    """Return the structure with the specified ligand residue removed (so the pocket
    is empty for redocking)."""
    want = (resname.strip().upper(), (chain or "_").strip() or "_", str(resnum))
    kept = []
    for line in pdb_text.splitlines():
        if line.startswith(("ATOM", "HETATM")) and _residue_key(line) == want:
            continue
        kept.append(line)
    return "\n".join(kept) + "\n"


# ---------------------------------------------------------------------------
# RMSD (alignment-free, symmetry-tolerant)
# ---------------------------------------------------------------------------

def _rmsd_rdkit(ref_pdb: str, pose_pdb: str) -> Optional[float]:
    """Exact symmetry-corrected, alignment-free RMSD via RDKit CalcRMS.

    Requires both molecules to parse to the same graph. Returns None if that
    can't be guaranteed (caller falls back to the Hungarian estimate).
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import rdMolAlign
    except ImportError:
        return None
    try:
        ref = Chem.MolFromPDBBlock(ref_pdb, removeHs=True, sanitize=False)
        prb = Chem.MolFromPDBBlock(pose_pdb, removeHs=True, sanitize=False)
        if ref is None or prb is None:
            return None
        if ref.GetNumAtoms() != prb.GetNumAtoms() or ref.GetNumAtoms() == 0:
            return None
        # CalcRMS computes RMSD without alignment, minimised over automorphisms.
        return round(float(rdMolAlign.CalcRMS(prb, ref)), 3)
    except Exception as exc:  # noqa: BLE001 - RDKit raises many concrete types
        logger.debug("RDKit CalcRMS unavailable for this pair: %s", exc)
        return None


def _rmsd_hungarian(ref_atoms, pose_atoms) -> Optional[float]:
    """Alignment-free RMSD using an optimal element-constrained atom assignment.

    Symmetry-tolerant lower-bound estimate that does not require identical graph
    perception. Uses scipy's Hungarian solver.
    """
    try:
        import numpy as np
        from scipy.optimize import linear_sum_assignment
    except ImportError:
        return None

    if not ref_atoms or not pose_atoms or len(ref_atoms) != len(pose_atoms):
        return None

    n = len(ref_atoms)
    ref_xyz = np.array([(x, y, z) for _, x, y, z in ref_atoms])
    pose_xyz = np.array([(x, y, z) for _, x, y, z in pose_atoms])
    ref_el = [e for e, *_ in ref_atoms]
    pose_el = [e for e, *_ in pose_atoms]

    # Squared-distance cost; forbid cross-element matches with a large penalty.
    diff = ref_xyz[:, None, :] - pose_xyz[None, :, :]
    cost = (diff ** 2).sum(axis=2)
    BIG = cost.max() * 1e6 + 1.0e9
    for i in range(n):
        for j in range(n):
            if ref_el[i] != pose_el[j]:
                cost[i, j] += BIG

    row, col = linear_sum_assignment(cost)
    # Reject if the optimal assignment had to cross elements (composition mismatch).
    if any(ref_el[i] != pose_el[j] for i, j in zip(row, col)):
        return None
    sq = ((ref_xyz[row] - pose_xyz[col]) ** 2).sum(axis=1)
    return round(float(np.sqrt(sq.mean())), 3)


def rmsd_to_reference(ref_pdb_block: str, pose_pdbqt_block: str) -> Tuple[Optional[float], Optional[str]]:
    """Compute heavy-atom RMSD between a docked pose and the crystal ligand.

    Returns (rmsd, method) where method is "rdkit", "hungarian", or None.
    """
    # Convert the docked PDBQT pose to PDB so both share a parser path.
    pose_pdb = None
    try:
        from core.openbabel_utils import convert_format
        pose_pdb = convert_format(pose_pdbqt_block, "pdbqt", "pdb")
    except Exception as exc:  # noqa: BLE001
        logger.debug("OpenBabel PDBQT→PDB conversion failed: %s", exc)

    if pose_pdb:
        exact = _rmsd_rdkit(ref_pdb_block, pose_pdb)
        if exact is not None:
            return exact, "rdkit"

    ref_atoms = _parse_heavy_atoms(ref_pdb_block)
    pose_atoms = _parse_heavy_atoms(pose_pdb or pose_pdbqt_block)
    approx = _rmsd_hungarian(ref_atoms, pose_atoms)
    if approx is not None:
        return approx, "hungarian"
    return None, None


def _classify(rmsd: Optional[float]) -> str:
    if rmsd is None:
        return "error"
    if rmsd <= RMSD_PASS:
        return "pass"
    if rmsd <= RMSD_AMBER:
        return "acceptable"
    return "fail"


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def _pick_ligand(report_dict: Dict[str, Any],
                 resname: Optional[str],
                 chain: Optional[str],
                 resnum: Optional[int]) -> Dict[str, Any]:
    ligands = report_dict.get("ligands", []) or []
    if not ligands:
        raise ValueError(
            "No co-crystallized ligand detected in this structure — redocking "
            "validation requires a bound reference ligand."
        )
    if resname is not None:
        for lig in ligands:
            if (lig.get("resname", "").upper() == resname.upper()
                    and (chain is None or lig.get("chain_id") == chain)
                    and (resnum is None or lig.get("resnum") == resnum)):
                return lig
        raise ValueError(f"Requested ligand {resname} {chain}:{resnum} not found among detected ligands.")
    # Default: the ligand with the most atoms (most likely the real substrate).
    return max(ligands, key=lambda l: l.get("num_atoms", 0))


def redock_validate(
    pdb_text: str,
    resname: Optional[str] = None,
    chain: Optional[str] = None,
    resnum: Optional[int] = None,
    exhaustiveness: int = 8,
    num_modes: int = 9,
    scoring_function: str = "vina",
    seed: Optional[int] = None,
    remove_water: bool = True,
) -> RedockValidationResult:
    """Run cognate redocking of a receptor's co-crystal ligand and report RMSD-to-crystal."""
    from docking_workflow.protein_analysis import (
        analyze_receptor,
        suggest_binding_site_from_ligand,
        LigandInfo,
    )
    from docking_workflow.protein_preparation import prepare_protein
    from docking_workflow.vina_runner import run_vina
    from docking_workflow.pose_manager import parse_vina_output
    from core.openbabel_utils import convert_format

    report = analyze_receptor(pdb_text).to_dict()
    lig = _pick_ligand(report, resname, chain, resnum)
    lig_resname = lig["resname"]
    lig_chain = lig.get("chain_id", "_")
    lig_resnum = int(lig.get("resnum", 0))

    def _err(msg: str) -> RedockValidationResult:
        return RedockValidationResult(
            status="error", rmsd=None, rmsd_method=None,
            reference_resname=lig_resname, reference_chain=lig_chain, reference_resnum=lig_resnum,
            best_affinity=None, grid=None, message=msg,
        )

    # Reference (crystal) pose + focused grid from that ligand.
    ref_ligand_pdb = extract_ligand_block(pdb_text, lig_resname, lig_chain, lig_resnum)
    site = suggest_binding_site_from_ligand(
        pdb_text,
        LigandInfo(resname=lig_resname, chain_id=lig_chain, resnum=lig_resnum,
                   num_atoms=lig.get("num_atoms", 0), centroid=lig.get("centroid")),
    )
    if site is None:
        return _err("Could not derive a binding-site grid box from the co-crystal ligand.")
    g = site.suggested_grid
    grid = {
        "center_x": g.center_x, "center_y": g.center_y, "center_z": g.center_z,
        "size_x": g.size_x, "size_y": g.size_y, "size_z": g.size_z,
    }

    # Empty the pocket, prepare the receptor, and prepare the native ligand for docking.
    receptor_pdb = strip_residue(pdb_text, lig_resname, lig_chain, lig_resnum)
    try:
        receptor_pdbqt = prepare_protein(receptor_pdb, remove_water=remove_water, add_charges=True)
    except Exception as exc:  # noqa: BLE001
        return _err(f"Receptor preparation failed: {exc}")

    try:
        ligand_pdbqt = convert_format(ref_ligand_pdb, "pdb", "pdbqt")
    except Exception as exc:  # noqa: BLE001
        return _err(f"Reference ligand preparation failed: {exc}")

    try:
        result = run_vina(
            receptor_pdbqt, ligand_pdbqt,
            grid["center_x"], grid["center_y"], grid["center_z"],
            grid["size_x"], grid["size_y"], grid["size_z"],
            exhaustiveness=exhaustiveness, num_modes=num_modes,
            scoring_function=scoring_function, seed=seed,
        )
    except Exception as exc:  # noqa: BLE001
        return _err(f"Vina redocking run failed: {exc}")

    poses = parse_vina_output(result.pdbqt_output)
    if not poses:
        return _err("Redocking produced no parseable poses.")

    top = poses[0]
    rmsd, method = rmsd_to_reference(ref_ligand_pdb, top.pdbqt_block)
    status = _classify(rmsd)

    if rmsd is None:
        message = (
            "Redocking completed but RMSD to the crystal ligand could not be computed "
            "(atom-count/perception mismatch between the prepared pose and the reference)."
        )
    else:
        label = {"pass": "trustworthy", "acceptable": "borderline", "fail": "not reproduced"}[status]
        message = (
            f"Redocked {lig_resname} reproduced the crystal pose to {rmsd} Å "
            f"({method}); protocol looks {label} (pass<{RMSD_PASS}Å, acceptable<{RMSD_AMBER}Å)."
        )

    return RedockValidationResult(
        status=status, rmsd=rmsd, rmsd_method=method,
        reference_resname=lig_resname, reference_chain=lig_chain, reference_resnum=lig_resnum,
        best_affinity=top.affinity_kcal, grid=grid, num_poses=len(poses), message=message,
    )
