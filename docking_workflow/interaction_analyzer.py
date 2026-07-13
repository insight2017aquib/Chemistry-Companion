"""
docking_workflow/interaction_analyzer.py
========================================
Geometry- and atom-type-based protein-ligand interaction detection.

Every PDBQT ATOM/HETATM line already carries a real AutoDock atom type as its
last field (OA, HD, NA, SA, A, C, N, O, Zn, ...) — this module classifies
donors/acceptors/aromatics/metals from that type instead of guessing from atom
*names*, and computes real geometry (H-bond D-H...A angle from an explicit
donor hydrogen, aromatic ring-plane angle for pi-stacking) instead of
reporting placeholder values.

Detected interaction types:
  - Hydrogen bonds (heavy-atom D...A < 3.5 Å; real D-H...A angle when an
    explicit polar hydrogen is present, heavy-atom-only otherwise)
  - Hydrophobic contacts (< 4.0 Å between aliphatic/aromatic carbons)
  - Pi-stacking (ring centroid distance + real ring-plane angle, both
    parallel/face-to-face and perpendicular/T-shaped geometries)
  - Salt bridges (ligand atom must itself be charged/ionizable — protonated
    amine or carboxylate/sulfonate-like oxygen pair — near a charged
    protein side-chain atom, not just "any atom near Asp/Glu/Lys/Arg")
  - Metal coordination (< 2.8 Å between a metal atom and a coordinating
    heteroatom)
  - Water bridges (ligand-water-protein H-bond networks)

Design goals:
- No new dependencies — pure Python + the atom typing AutoDock/Vina already
  writes into every PDBQT file.
- Graceful degradation: if a criterion can't be evaluated (no explicit
  hydrogens present, insufficient ring atoms for a plane fit), the
  interaction is either omitted or reported with real fields left as None —
  never a fabricated number standing in for an unmeasured quantity.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Re-export the simple Interaction dataclass so callers can keep using it
from .interaction_mapper import Interaction  # noqa: F401


# ---------------------------------------------------------------------------
# Geometric criteria (reasonable defaults used across the field)
# ---------------------------------------------------------------------------
H_BOND_DISTANCE_CUTOFF = 3.5   # Å (heavy-atom donor...acceptor)
H_BOND_ANGLE_MIN = 120.0       # degrees (D-H...A), only enforced when H is known

HYDROPHOBIC_DISTANCE_CUTOFF = 4.0  # Å

SALT_BRIDGE_DISTANCE_CUTOFF = 4.0  # Å (charged-atom to charged-atom)

PI_STACKING_CENTROID_CUTOFF_PARALLEL = 5.5   # Å
PI_STACKING_CENTROID_CUTOFF_TSHAPED = 6.5    # Å
PI_STACKING_PARALLEL_ANGLE_MAX = 30.0        # degrees from co-planar
PI_STACKING_TSHAPED_ANGLE_MIN = 60.0         # degrees from co-planar
PI_STACKING_TSHAPED_ANGLE_MAX = 120.0

METAL_COORDINATION_DISTANCE_CUTOFF = 2.8  # Å
WATER_BRIDGE_DISTANCE_CUTOFF = 3.5        # Å

BONDED_H_DISTANCE = 1.2   # Å, heavy-atom to its own hydrogen
CHARGE_PAIR_DISTANCE = 2.4  # Å, e.g. the two O's of a carboxylate

# AutoDock/Vina atom types (last whitespace-separated field of a PDBQT line)
ACCEPTOR_TYPES = {"OA", "NA", "SA"}
DONOR_ELEMENT_TYPES = {"N", "NA", "O", "OA"}  # heavy atoms that can bear a donor H
POLAR_H_TYPE = "HD"
AROMATIC_TYPE = "A"
ALIPHATIC_HYDROPHOBIC_TYPES = {"C", "A"}
METAL_TYPES = {"ZN", "MG", "CA", "FE", "MN", "CU", "NI", "CO", "CD", "HG", "NA_ION", "K"}

WATER_RESNAMES = {"HOH", "WAT", "H2O", "WTR"}

# Protein side-chain atoms that carry a formal/partial charge at physiological pH
ANIONIC_RESIDUE_ATOMS = {
    ("ASP", "OD1"), ("ASP", "OD2"),
    ("GLU", "OE1"), ("GLU", "OE2"),
}
CATIONIC_RESIDUE_ATOMS = {
    ("LYS", "NZ"),
    ("ARG", "NH1"), ("ARG", "NH2"), ("ARG", "NE"),
    ("HIS", "ND1"), ("HIS", "NE2"),
}

# Aromatic ring atoms used for pi-stacking plane fitting
AROMATIC_RING_ATOMS = {
    "PHE": ["CG", "CD1", "CD2", "CE1", "CE2", "CZ"],
    "TYR": ["CG", "CD1", "CD2", "CE1", "CE2", "CZ"],
    "TRP": ["CD2", "CE2", "CE3", "CZ2", "CZ3", "CH2"],  # six-membered ring of the indole
}


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _atom_type(line: str) -> str:
    """Return the AutoDock atom type (the last whitespace-separated field)."""
    parts = line.split()
    return parts[-1].strip() if parts else ""


def _parse_pdbqt_atoms(pdbqt_text: str) -> List[dict]:
    """
    Parse ATOM/HETATM records into dicts with real AutoDock atom typing.
    Returns: atom_name, resname, chain, resnum, x, y, z, atom_type
    """
    atoms = []
    for line in pdbqt_text.splitlines():
        if not (line.startswith("ATOM") or line.startswith("HETATM")):
            continue
        try:
            atoms.append({
                "atom_name": line[12:16].strip(),
                "resname": line[17:20].strip().upper(),
                "chain": line[21:22].strip() or " ",
                "resnum": int(line[22:26].strip() or "0"),
                "x": float(line[30:38]),
                "y": float(line[38:46]),
                "z": float(line[46:54]),
                "atom_type": _atom_type(line),
            })
        except (ValueError, IndexError):
            continue
    return atoms


def _dist(a: dict, b: dict) -> float:
    return math.sqrt((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2 + (a["z"] - b["z"]) ** 2)


def _vec(a: dict, b: dict) -> Tuple[float, float, float]:
    return (b["x"] - a["x"], b["y"] - a["y"], b["z"] - a["z"])


def _angle_deg(p_h: dict, p_donor: dict, p_acceptor: dict) -> float:
    """Angle at the hydrogen between H->donor and H->acceptor, in degrees."""
    v1 = _vec(p_h, p_donor)
    v2 = _vec(p_h, p_acceptor)
    dot = v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]
    n1 = math.sqrt(sum(c * c for c in v1))
    n2 = math.sqrt(sum(c * c for c in v2))
    if n1 == 0 or n2 == 0:
        return 0.0
    cos_theta = max(-1.0, min(1.0, dot / (n1 * n2)))
    return math.degrees(math.acos(cos_theta))


def _find_bonded_hydrogen(heavy_atom: dict, atoms: List[dict]) -> Optional[dict]:
    """Find an HD atom bonded to this heavy atom (within normal bond length)."""
    best = None
    best_dist = BONDED_H_DISTANCE
    for atom in atoms:
        if atom["atom_type"] != POLAR_H_TYPE:
            continue
        d = _dist(heavy_atom, atom)
        if d < best_dist:
            best_dist = d
            best = atom
    return best


def _is_cationic_ligand_atom(atom: dict, all_ligand_atoms: List[dict]) -> bool:
    """A protonated nitrogen (has a bonded donor hydrogen) reads as a cationic site."""
    if atom["atom_type"] not in ("N", "NA"):
        return False
    return _find_bonded_hydrogen(atom, all_ligand_atoms) is not None


def _is_anionic_ligand_atom(atom: dict, all_ligand_atoms: List[dict]) -> bool:
    """Two acceptor oxygens close together reads as a carboxylate/phosphate/sulfonate-like anion."""
    if atom["atom_type"] != "OA":
        return False
    for other in all_ligand_atoms:
        if other is atom or other["atom_type"] != "OA":
            continue
        if _dist(atom, other) < CHARGE_PAIR_DISTANCE:
            return True
    return False


def _ring_plane(atoms: List[Tuple[float, float, float]]) -> Optional[Tuple[Tuple[float, float, float], Tuple[float, float, float]]]:
    """
    Fit a plane to a set of ring atoms using simple centroid + cross-product
    normal (average of consecutive-triple normals) — no numpy dependency.
    Returns (centroid, normal) or None if too few atoms.
    """
    if len(atoms) < 3:
        return None
    n = len(atoms)
    cx = sum(a[0] for a in atoms) / n
    cy = sum(a[1] for a in atoms) / n
    cz = sum(a[2] for a in atoms) / n
    centroid = (cx, cy, cz)

    nx = ny = nz = 0.0
    for i in range(n):
        x1, y1, z1 = atoms[i]
        x2, y2, z2 = atoms[(i + 1) % n]
        v1 = (x1 - cx, y1 - cy, z1 - cz)
        v2 = (x2 - cx, y2 - cy, z2 - cz)
        cross = (
            v1[1] * v2[2] - v1[2] * v2[1],
            v1[2] * v2[0] - v1[0] * v2[2],
            v1[0] * v2[1] - v1[1] * v2[0],
        )
        nx += cross[0]
        ny += cross[1]
        nz += cross[2]

    norm_len = math.sqrt(nx * nx + ny * ny + nz * nz)
    if norm_len == 0:
        return None
    return centroid, (nx / norm_len, ny / norm_len, nz / norm_len)


def _plane_angle_deg(n1: Tuple[float, float, float], n2: Tuple[float, float, float]) -> float:
    dot = max(-1.0, min(1.0, n1[0] * n2[0] + n1[1] * n2[1] + n1[2] * n2[2]))
    angle = math.degrees(math.acos(abs(dot)))  # fold to 0-90 range (normals are directionless)
    return angle


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------

def find_interactions(
    protein_pdbqt: str,
    ligand_block: str,
    ligand_format: str = "pdbqt",
) -> List[Interaction]:
    """
    Detect non-covalent interactions between a protein (PDBQT) and a docked pose.

    Both protein_pdbqt and ligand_block must be PDBQT text (with real AutoDock
    atom types) for the type-based detection to work. A non-PDBQT ligand_block
    (e.g. SDF) will yield no interactions, since element/donor-acceptor
    information isn't recoverable from atom names alone.
    """
    if not protein_pdbqt or not ligand_block:
        return []

    protein_atoms = _parse_pdbqt_atoms(protein_pdbqt)
    if not protein_atoms:
        logger.warning("No parseable protein atoms found for interaction analysis.")
        return []

    if ligand_format.lower() != "pdbqt":
        logger.debug("Interaction analysis requires PDBQT atom typing; got format=%s.", ligand_format)
        return []

    ligand_atoms = _parse_pdbqt_atoms(ligand_block)
    if not ligand_atoms:
        return []

    interactions: List[Interaction] = []

    protein_heavy = [a for a in protein_atoms if a["resname"] not in WATER_RESNAMES]
    protein_waters = [a for a in protein_atoms if a["resname"] in WATER_RESNAMES]
    protein_metals = [a for a in protein_atoms if a["atom_type"].upper() in METAL_TYPES]

    interactions.extend(_find_hbonds(protein_heavy, ligand_atoms, protein_atoms, ligand_atoms))
    interactions.extend(_find_hydrophobic(protein_heavy, ligand_atoms))
    interactions.extend(_find_salt_bridges(protein_heavy, ligand_atoms))
    interactions.extend(_find_metal_coordination(protein_metals, ligand_atoms))
    interactions.extend(_find_water_bridges(protein_waters, protein_heavy, ligand_atoms))
    interactions.extend(_find_pi_stacking(protein_atoms, ligand_atoms))

    # Deduplicate and sort by distance
    seen = set()
    unique = []
    for ia in sorted(interactions, key=lambda x: x.distance):
        key = (ia.type, ia.protein_residue, ia.ligand_atom)
        if key not in seen:
            seen.add(key)
            unique.append(ia)

    return unique[:25]  # cap noise


def _find_hbonds(protein_heavy, ligand_atoms, all_protein_atoms, all_ligand_atoms) -> List[Interaction]:
    interactions: List[Interaction] = []

    def evaluate(donor_side, donor_all, acceptor_side, acceptor_all, protein_is_donor: bool):
        for donor in donor_side:
            if donor["atom_type"] not in DONOR_ELEMENT_TYPES:
                continue
            bonded_h = _find_bonded_hydrogen(donor, donor_all)
            for acceptor in acceptor_side:
                if acceptor["atom_type"] not in ACCEPTOR_TYPES:
                    continue
                dist = _dist(donor, acceptor)
                if dist >= H_BOND_DISTANCE_CUTOFF:
                    continue

                angle = None
                if bonded_h is not None:
                    angle = _angle_deg(bonded_h, donor, acceptor)
                    if angle < H_BOND_ANGLE_MIN:
                        continue  # geometry doesn't look like a real H-bond

                res_label = f"{donor['resname']} {donor['resnum']}" if protein_is_donor else f"{acceptor['resname']} {acceptor['resnum']}"
                lig_atom = donor["atom_name"] if not protein_is_donor else acceptor["atom_name"]
                interactions.append(Interaction(
                    type="H-bond",
                    protein_residue=res_label,
                    ligand_atom=lig_atom or "?",
                    distance=round(dist, 2),
                    angle=round(angle, 1) if angle is not None else None,
                ))

    # Protein donates to ligand
    evaluate(protein_heavy, all_protein_atoms, ligand_atoms, all_ligand_atoms, protein_is_donor=True)
    # Ligand donates to protein
    evaluate(ligand_atoms, all_ligand_atoms, protein_heavy, all_protein_atoms, protein_is_donor=False)

    return interactions


def _find_hydrophobic(protein_heavy, ligand_atoms) -> List[Interaction]:
    interactions = []
    for res in protein_heavy:
        if res["atom_type"] not in ALIPHATIC_HYDROPHOBIC_TYPES:
            continue
        for lig in ligand_atoms:
            if lig["atom_type"] not in ALIPHATIC_HYDROPHOBIC_TYPES:
                continue
            dist = _dist(res, lig)
            if dist < HYDROPHOBIC_DISTANCE_CUTOFF:
                interactions.append(Interaction(
                    type="Hydrophobic",
                    protein_residue=f"{res['resname']} {res['resnum']}",
                    ligand_atom=lig["atom_name"] or "?",
                    distance=round(dist, 2),
                ))
    return interactions


def _find_salt_bridges(protein_heavy, ligand_atoms) -> List[Interaction]:
    """Requires the ligand atom to itself be charged/ionizable (protonated amine or
    carboxylate/sulfonate-like oxygen pair), not just proximity to a charged residue."""
    interactions = []
    for lig in ligand_atoms:
        is_cationic = _is_cationic_ligand_atom(lig, ligand_atoms)
        is_anionic = _is_anionic_ligand_atom(lig, ligand_atoms)
        if not is_cationic and not is_anionic:
            continue

        target_atoms = ANIONIC_RESIDUE_ATOMS if is_cationic else CATIONIC_RESIDUE_ATOMS
        for res in protein_heavy:
            if (res["resname"], res["atom_name"]) not in target_atoms:
                continue
            dist = _dist(res, lig)
            if dist < SALT_BRIDGE_DISTANCE_CUTOFF:
                interactions.append(Interaction(
                    type="Salt Bridge",
                    protein_residue=f"{res['resname']} {res['resnum']}",
                    ligand_atom=lig["atom_name"] or "?",
                    distance=round(dist, 2),
                ))
    return interactions


def _find_metal_coordination(protein_metals, ligand_atoms) -> List[Interaction]:
    interactions = []
    for metal in protein_metals:
        for lig in ligand_atoms:
            if lig["atom_type"] not in ACCEPTOR_TYPES and lig["atom_type"] not in ("N", "S", "SA"):
                continue
            dist = _dist(metal, lig)
            if dist < METAL_COORDINATION_DISTANCE_CUTOFF:
                interactions.append(Interaction(
                    type="Metal Coordination",
                    protein_residue=f"{metal['resname']} {metal['resnum']}",
                    ligand_atom=lig["atom_name"] or "?",
                    distance=round(dist, 2),
                ))
    return interactions


def _find_water_bridges(protein_waters, protein_heavy, ligand_atoms) -> List[Interaction]:
    interactions = []
    for water in protein_waters:
        for lig in ligand_atoms:
            if lig["atom_type"] not in DONOR_ELEMENT_TYPES and lig["atom_type"] not in ACCEPTOR_TYPES:
                continue
            dist_to_ligand = _dist(water, lig)
            if dist_to_ligand >= WATER_BRIDGE_DISTANCE_CUTOFF:
                continue
            for res in protein_heavy:
                if res["atom_type"] not in DONOR_ELEMENT_TYPES and res["atom_type"] not in ACCEPTOR_TYPES:
                    continue
                if _dist(water, res) < WATER_BRIDGE_DISTANCE_CUTOFF:
                    interactions.append(Interaction(
                        type="Water Bridge",
                        protein_residue=f"{res['resname']} {res['resnum']} (via water {water['resnum']})",
                        ligand_atom=lig["atom_name"] or "?",
                        distance=round(dist_to_ligand, 2),
                    ))
                    break
    return interactions


def _find_pi_stacking(protein_atoms, ligand_atoms) -> List[Interaction]:
    """Real ring-plane geometry: fits a plane to the protein aromatic ring and to a
    cluster of nearby ligand aromatic ('A'-typed) atoms, then classifies by the
    angle between the two ring normals (parallel/face-to-face vs. T-shaped/edge-to-face)."""
    interactions = []

    by_residue: dict = {}
    for atom in protein_atoms:
        if atom["resname"] not in AROMATIC_RING_ATOMS:
            continue
        key = (atom["resname"], atom["chain"], atom["resnum"])
        by_residue.setdefault(key, {})[atom["atom_name"]] = atom

    ligand_aromatic = [a for a in ligand_atoms if a["atom_type"] == AROMATIC_TYPE]
    if not ligand_aromatic:
        return interactions

    for (resname, chain, resnum), atom_map in by_residue.items():
        ring_names = AROMATIC_RING_ATOMS[resname]
        ring_atoms = [atom_map[n] for n in ring_names if n in atom_map]
        if len(ring_atoms) < 5:  # need most of the ring present to trust the plane fit
            continue

        ring_coords = [(a["x"], a["y"], a["z"]) for a in ring_atoms]
        protein_plane = _ring_plane(ring_coords)
        if protein_plane is None:
            continue
        protein_centroid, protein_normal = protein_plane

        # Cluster nearby ligand aromatic atoms (within a generous radius of the ring centroid)
        centroid_atom = {"x": protein_centroid[0], "y": protein_centroid[1], "z": protein_centroid[2]}
        nearby_ligand_aromatic = [a for a in ligand_aromatic if _dist(centroid_atom, a) < 7.0]
        if len(nearby_ligand_aromatic) < 3:
            continue

        ligand_coords = [(a["x"], a["y"], a["z"]) for a in nearby_ligand_aromatic]
        ligand_plane = _ring_plane(ligand_coords)
        if ligand_plane is None:
            continue
        ligand_centroid, ligand_normal = ligand_plane

        centroid_dist = math.sqrt(sum((p - l) ** 2 for p, l in zip(protein_centroid, ligand_centroid)))
        plane_angle = _plane_angle_deg(protein_normal, ligand_normal)

        stack_type = None
        if centroid_dist < PI_STACKING_CENTROID_CUTOFF_PARALLEL and plane_angle <= PI_STACKING_PARALLEL_ANGLE_MAX:
            stack_type = "Pi-Stacking (parallel)"
        elif centroid_dist < PI_STACKING_CENTROID_CUTOFF_TSHAPED and PI_STACKING_TSHAPED_ANGLE_MIN <= plane_angle <= PI_STACKING_TSHAPED_ANGLE_MAX:
            stack_type = "Pi-Stacking (T-shaped)"

        if stack_type:
            closest_ligand_atom = min(nearby_ligand_aromatic, key=lambda a: _dist(centroid_atom, a))
            interactions.append(Interaction(
                type=stack_type,
                protein_residue=f"{resname} {resnum}",
                ligand_atom=closest_ligand_atom["atom_name"] or "?",
                distance=round(centroid_dist, 2),
                angle=round(plane_angle, 1),
            ))

    return interactions


# ---------------------------------------------------------------------------
# Convenience wrapper that keeps the old public API working
# ---------------------------------------------------------------------------

def map_interactions(protein_pdb: str, pose_pdbqt: str) -> List[Interaction]:
    """
    Drop-in replacement for the old mock function.
    Delegates to the real analyzer.
    """
    return find_interactions(protein_pdb, pose_pdbqt, ligand_format="pdbqt")
