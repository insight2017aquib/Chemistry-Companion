"""
Tests for the Advanced Docking additions (P1, P3, P5, P7).

These cover the pure-Python logic that does not require the Vina CLI, OpenBabel,
or a GPU: pKd conversion, grid-box whole-receptor guard, RMSD/extraction helpers
for redocking validation, and interaction-fingerprint comparison.
"""

import math
import os

from docking_workflow.report_builder import affinity_to_pkd
from docking_workflow.gridbox_builder import auto_gridbox, _WHOLE_RECEPTOR_DIMENSION
from docking_workflow.redock_validation import (
    _parse_heavy_atoms,
    _rmsd_hungarian,
    extract_ligand_block,
    strip_residue,
    _classify,
    RMSD_PASS,
    RMSD_AMBER,
)
from docking_workflow.interaction_fingerprint import (
    fingerprint,
    compare_interactions,
)


# ── P5: affinity → pKd ───────────────────────────────────────────────

def test_affinity_to_pkd_basic():
    # -8.184 kcal/mol / 1.364 ≈ 6.0
    assert affinity_to_pkd(-8.184) == 6.0


def test_affinity_to_pkd_rejects_nonnegative_and_none():
    assert affinity_to_pkd(None) is None
    assert affinity_to_pkd(0.0) is None
    assert affinity_to_pkd(1.5) is None


# ── P7: grid box whole-receptor guard ────────────────────────────────

def _pdbqt_from_points(points):
    lines = []
    for i, (x, y, z) in enumerate(points, start=1):
        lines.append(
            f"ATOM  {i:>5} C   LIG A   1    "
            f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00  0.00           C"
        )
    return "\n".join(lines) + "\n"


def test_auto_gridbox_small_site_no_warning():
    pts = [(0, 0, 0), (2, 0, 0), (0, 2, 0), (0, 0, 2)]
    cfg = auto_gridbox(_pdbqt_from_points(pts), margin=5.0)
    assert cfg.warning is None
    assert cfg.size_x < _WHOLE_RECEPTOR_DIMENSION


def test_auto_gridbox_whole_receptor_warns():
    pts = [(-30, 0, 0), (30, 0, 0), (0, -25, 0), (0, 25, 0)]
    cfg = auto_gridbox(_pdbqt_from_points(pts), margin=5.0)
    assert cfg.warning is not None
    assert "blind docking" in cfg.warning.lower()


# ── P1: extraction / stripping ───────────────────────────────────────

_SAMPLE_PDB = """\
ATOM      1  N   ALA A   1      11.000  11.000  11.000  1.00  0.00           N
ATOM      2  CA  ALA A   1      12.000  11.000  11.000  1.00  0.00           C
HETATM    3  C1  LIG A 900       0.000   0.000   0.000  1.00  0.00           C
HETATM    4  O1  LIG A 900       1.500   0.000   0.000  1.00  0.00           O
HETATM    5  O   HOH A 950       5.000   5.000   5.000  1.00  0.00           O
"""


def test_extract_ligand_block_only_ligand():
    block = extract_ligand_block(_SAMPLE_PDB, "LIG", "A", 900)
    atoms = _parse_heavy_atoms(block)
    assert len(atoms) == 2
    elements = sorted(e for e, *_ in atoms)
    assert elements == ["C", "O"]


def test_strip_residue_removes_ligand_keeps_rest():
    stripped = strip_residue(_SAMPLE_PDB, "LIG", "A", 900)
    assert "LIG A 900" not in stripped
    assert "ALA A   1" in stripped
    assert "HOH A 950" in stripped


def test_extract_missing_ligand_raises():
    try:
        extract_ligand_block(_SAMPLE_PDB, "XXX", "A", 1)
    except ValueError:
        return
    raise AssertionError("Expected ValueError for missing ligand")


# ── P1: RMSD (Hungarian, alignment-free, symmetry-tolerant) ──────────

def test_rmsd_identical_is_zero():
    atoms = [("C", 0.0, 0.0, 0.0), ("O", 1.5, 0.0, 0.0), ("N", 0.0, 1.5, 0.0)]
    assert _rmsd_hungarian(atoms, list(atoms)) == 0.0


def test_rmsd_uniform_shift():
    ref = [("C", 0.0, 0.0, 0.0), ("O", 1.0, 0.0, 0.0)]
    # Shift every atom by 1 Å in x → RMSD should be exactly 1.0
    pose = [("C", 1.0, 0.0, 0.0), ("O", 2.0, 0.0, 0.0)]
    assert math.isclose(_rmsd_hungarian(ref, pose), 1.0, abs_tol=1e-6)


def test_rmsd_symmetry_tolerant_matching():
    # Two identical-element atoms swapped in order should still match optimally.
    ref = [("O", 0.0, 0.0, 0.0), ("O", 3.0, 0.0, 0.0)]
    pose = [("O", 3.0, 0.0, 0.0), ("O", 0.0, 0.0, 0.0)]
    assert _rmsd_hungarian(ref, pose) == 0.0


def test_rmsd_count_mismatch_returns_none():
    ref = [("C", 0.0, 0.0, 0.0)]
    pose = [("C", 0.0, 0.0, 0.0), ("O", 1.0, 0.0, 0.0)]
    assert _rmsd_hungarian(ref, pose) is None


def test_classify_thresholds():
    assert _classify(1.0) == "pass"
    assert _classify(RMSD_PASS) == "pass"
    assert _classify(2.5) == "acceptable"
    assert _classify(RMSD_AMBER) == "acceptable"
    assert _classify(4.0) == "fail"
    assert _classify(None) == "error"


# ── P3: interaction fingerprint ──────────────────────────────────────

def test_fingerprint_normalizes_types_and_waters():
    interactions = [
        {"type": "Pi-Stacking (T-shaped)", "protein_residue": "PHE 382"},
        {"type": "H-bond", "protein_residue": "THR 315 (via water 501)"},
    ]
    fp = fingerprint(interactions)
    assert ("pi-stacking", "PHE 382") in fp
    assert ("h-bond", "THR 315") in fp


def test_compare_interactions_similarity_and_buckets():
    reference = [
        {"type": "H-bond", "protein_residue": "ASP 100"},
        {"type": "Hydrophobic", "protein_residue": "LEU 200"},
    ]
    pose = [
        {"type": "H-bond", "protein_residue": "ASP 100"},   # reproduced
        {"type": "Salt Bridge", "protein_residue": "LYS 300"},  # new
    ]
    cmp = compare_interactions(reference, pose)
    # 1 shared out of 3 union → 1/3
    assert math.isclose(cmp.similarity, 1 / 3, abs_tol=1e-6)
    assert {"type": "h-bond", "residue": "ASP 100"} in cmp.reproduced
    assert {"type": "hydrophobic", "residue": "LEU 200"} in cmp.missed
    assert {"type": "salt-bridge", "residue": "LYS 300"} in cmp.new


def test_compare_interactions_empty():
    cmp = compare_interactions([], [])
    assert cmp.similarity == 0.0
    assert cmp.reproduced == []


# ── Receptor preparation: co-crystal ligand removal (audit fix) ──────

from docking_workflow.protein_preparation import (
    _classify_and_filter_pdb,
    _remove_ligand_records,
)

_PREP_PDB = (
    "ATOM      1  N   ALA A   1      11.000  11.000  11.000  1.00  0.00           N\n"
    "ATOM      2  CA  ALA A   1      12.000  11.000  11.000  1.00  0.00           C\n"
    "ATOM      3  N   HIS A   2      13.000  11.000  11.000  1.00  0.00           N\n"
    "HETATM    4  C1  LIG A 900       0.000   0.000   0.000  1.00  0.00           C\n"
    "HETATM    5  O1  LIG A 900       1.500   0.000   0.000  1.00  0.00           O\n"
    "HETATM    6  O   HOH A 950       5.000   5.000   5.000  1.00  0.00           O\n"
    "HETATM    7 ZN    ZN A 800       2.000   2.000   2.000  1.00  0.00          ZN\n"
)


def _kept_resnames(pdb_text):
    return sorted({
        line[17:20].strip()
        for line in pdb_text.splitlines()
        if line.startswith(("ATOM", "HETATM"))
    })


def test_filter_removes_cocrystal_ligand_keeps_protein():
    out, removed = _classify_and_filter_pdb(
        _PREP_PDB, remove_water=True, keep_cofactors=False, keep_metals=True,
        keep_active_site_waters=False, remove_bulk_waters=True, remove_ligands=True,
    )
    kept = _kept_resnames(out)
    # Regression guard: standard amino acids classify as the "ligand" catch-all but
    # must NEVER be removed (they are ATOM records, not HETATM co-crystal ligands).
    assert "ALA" in kept and "HIS" in kept
    assert "LIG" not in kept        # co-crystal ligand removed
    assert "HOH" not in kept        # water removed
    assert "ZN" in kept             # metal retained (keep_metals=True)
    assert removed["ligand"] == 2


def test_filter_keep_ligand_opt_in():
    out, _ = _classify_and_filter_pdb(
        _PREP_PDB, remove_water=True, keep_cofactors=False, keep_metals=True,
        keep_active_site_waters=False, remove_bulk_waters=True, remove_ligands=False,
    )
    assert "LIG" in _kept_resnames(out)


def test_remove_ligand_records_only_touches_hetatm_ligands():
    out = _remove_ligand_records(_PREP_PDB)
    kept = _kept_resnames(out)
    assert "ALA" in kept and "HIS" in kept   # protein untouched
    assert "LIG" not in kept                 # ligand stripped
    assert "HOH" in kept and "ZN" in kept     # waters/metals left to other logic


# ── OpenBabel binary resolver (Tier-1 fix #1) ────────────────────────

from docking_workflow.protein_preparation import _resolve_obabel_binary


def test_obabel_resolver_honors_env(tmp_path, monkeypatch):
    fake = tmp_path / ("obabel.exe" if os.name == "nt" else "obabel")
    fake.write_text("", encoding="utf-8")
    monkeypatch.setenv("OBABEL_BINARY", str(fake))
    assert _resolve_obabel_binary() == str(fake)


def test_obabel_resolver_returns_name_when_absent(monkeypatch):
    # With no env override and nothing installed on PATH, it degrades to the bare
    # name so the caller's FileNotFoundError handler emits its install message.
    monkeypatch.delenv("OBABEL_BINARY", raising=False)
    monkeypatch.delenv("OBABEL_EXE", raising=False)
    result = _resolve_obabel_binary()
    assert isinstance(result, str) and "obabel" in result.lower()
