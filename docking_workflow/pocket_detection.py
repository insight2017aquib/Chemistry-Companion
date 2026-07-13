"""
docking_workflow/pocket_detection.py
====================================

Phase 3B: Pocket-based binding site detection.

This module provides automatic detection of potential binding pockets
when no co-crystallized ligand is present in the structure.

Primary tool: fpocket (free, open-source, easy to install via conda)
Fallback: None (graceful degradation with clear messaging)

The goal is to suggest high-quality grid boxes for blind or semi-blind docking.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class Pocket:
    """Represents a predicted binding pocket."""
    pocket_id: int
    score: float                    # fpocket score (higher = better)
    center: Dict[str, float]        # {"x": , "y": , "z": }
    radius: float
    volume: Optional[float] = None
    druggability_score: Optional[float] = None
    residue_ids: List[str] = None   # e.g. ["A:45", "A:46", "B:12"]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _is_fpocket_available() -> bool:
    """Check if fpocket binary is available in PATH."""
    return shutil.which("fpocket") is not None


def _run_fpocket(pdb_path: str, output_dir: str) -> bool:
    """Run fpocket on a PDB file."""
    cmd = ["fpocket", "-f", pdb_path]
    try:
        result = subprocess.run(
            cmd,
            cwd=output_dir,
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode != 0:
            logger.warning("fpocket failed: %s", result.stderr)
            return False
        return True
    except subprocess.TimeoutExpired:
        logger.error("fpocket timed out")
        return False
    except Exception as e:
        logger.error("Failed to run fpocket: %s", e)
        return False


def _parse_fpocket_results(pockets_dir: str) -> List[Pocket]:
    """
    Parse fpocket output directory and return list of Pocket objects.
    fpocket creates pockets/pocketX_info.txt files.
    """
    pockets: List[Pocket] = []
    info_dir = os.path.join(pockets_dir, "pockets")

    if not os.path.isdir(info_dir):
        return pockets

    for filename in sorted(os.listdir(info_dir)):
        if not filename.endswith("_info.txt"):
            continue

        filepath = os.path.join(info_dir, filename)
        try:
            with open(filepath, "r") as f:
                content = f.read()

            pocket = _parse_single_pocket_info(content, filename)
            if pocket:
                pockets.append(pocket)
        except Exception as e:
            logger.warning("Failed to parse %s: %s", filename, e)
            continue

    # Sort by score descending
    pockets.sort(key=lambda p: p.score, reverse=True)
    return pockets


def _parse_single_pocket_info(content: str, filename: str) -> Optional[Pocket]:
    """Parse a single fpocket pocket info file."""
    data = {}
    for line in content.splitlines():
        line = line.strip()
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().lower().replace(" ", "_")
            value = value.strip()
            data[key] = value

    try:
        pocket_id = int(data.get("pocket", "0").split()[-1])
        score = float(data.get("score", 0.0))

        # Center
        cx = float(data.get("center_of_mass_x", 0))
        cy = float(data.get("center_of_mass_y", 0))
        cz = float(data.get("center_of_mass_z", 0))

        radius = float(data.get("radius", 5.0))
        volume = float(data.get("volume", 0)) if "volume" in data else None
        druggability = float(data.get("druggability_score", 0)) if "druggability_score" in data else None

        # Residues are harder to parse reliably from text.
        # For now we leave residue_ids empty; can be improved later.
        residue_ids: List[str] = []

        return Pocket(
            pocket_id=pocket_id,
            score=round(score, 3),
            center={"x": round(cx, 3), "y": round(cy, 3), "z": round(cz, 3)},
            radius=round(radius, 2),
            volume=round(volume, 1) if volume else None,
            druggability_score=round(druggability, 3) if druggability else None,
            residue_ids=residue_ids
        )
    except Exception as e:
        logger.debug("Failed to parse pocket info: %s", e)
        return None


def detect_pockets(pdb_text: str) -> List[Pocket]:
    """
    Main public function for Phase 3B.

    Attempts to detect binding pockets using fpocket.
    Returns a list of Pocket objects (sorted by score descending).

    If fpocket is not installed or fails, returns an empty list.
    The caller is responsible for checking the length and showing
    appropriate UI messages.
    """
    if not _is_fpocket_available():
        logger.info("fpocket not found in PATH. Pocket detection unavailable.")
        return []

    with tempfile.TemporaryDirectory() as tmpdir:
        pdb_path = os.path.join(tmpdir, "input.pdb")
        with open(pdb_path, "w", encoding="utf-8") as f:
            f.write(pdb_text)

        success = _run_fpocket(pdb_path, tmpdir)
        if not success:
            return []

        # fpocket creates a directory named after the input file + _out
        base_name = os.path.splitext(os.path.basename(pdb_path))[0]
        pockets_dir = os.path.join(tmpdir, f"{base_name}_out")

        if not os.path.isdir(pockets_dir):
            logger.warning("fpocket did not produce expected output directory")
            return []

        pockets = _parse_fpocket_results(pockets_dir)
        logger.info("fpocket detected %d pockets", len(pockets))
        return pockets


def pockets_to_suggestions(pockets: List[Pocket], top_n: int = 3) -> List[Dict[str, Any]]:
    """
    Convert Pocket objects into a format similar to BindingSiteSuggestion
    so the frontend can treat ligand sites and predicted pockets uniformly.
    """
    suggestions = []
    for pocket in pockets[:top_n]:
        size = max(22.0, pocket.radius * 2.2)

        suggestions.append({
            "type": "predicted_pocket",
            "pocket_id": pocket.pocket_id,
            "score": pocket.score,
            "center": pocket.center,
            "radius": pocket.radius,
            "suggested_grid": {
                "center_x": pocket.center["x"],
                "center_y": pocket.center["y"],
                "center_z": pocket.center["z"],
                "size_x": size,
                "size_y": size,
                "size_z": size,
            },
            "druggability_score": pocket.druggability_score,
            "label": f"Pocket {pocket.pocket_id} (score: {pocket.score:.2f})"
        })
    return suggestions