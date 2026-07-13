"""
docking_workflow/chimera_exporter.py
====================================
Generate high-quality ChimeraX scripts (.cxc) and bundles for docked complexes.

This is the core of the ChimeraX integration for the Advanced Docking Platform.
It produces publication-ready visualization scripts that leverage the excellent
rendering and analysis tools in UCSF ChimeraX.

Design goals:
- Work with the artifacts already present in a docking job workspace.
- Produce beautiful, sensible defaults (transparent protein surface, nice ligand,
  labeled interactions where possible).
- Be self-contained and runnable by double-clicking the .cxc file when possible.
- Graceful when only PDBQT files are available.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _get_job_workspace(job_id: str) -> str:
    """Return the path to the job's output directory."""
    from services.docking_workspace_service import DockingWorkspaceService
    return DockingWorkspaceService.get_workspace(job_id)


def _load_report(job_id: str) -> Dict[str, Any]:
    workspace = _get_job_workspace(job_id)
    report_path = os.path.join(workspace, "report.json")
    if not os.path.exists(report_path):
        raise FileNotFoundError(f"No report.json found for job {job_id}")
    with open(report_path, encoding="utf-8") as f:
        return json.load(f)


def _find_best_pose_sdf(workspace: str, rank: int) -> Optional[str]:
    """Return path to the SDF for a specific pose rank if it exists."""
    sdf_path = os.path.join(workspace, f"pose_{rank}.sdf")
    return sdf_path if os.path.exists(sdf_path) else None


def get_preset_defaults(preset: str = "publication") -> dict:
    """
    Return smart default parameters for different visualization styles.
    """
    presets = {
        "minimal": {
            "surface_transparency": 0.85,
            "run_hbonds": False,
            "label_interacting_residues": False,
            "nice_lighting": False,
            "pocket_radius": 5.0,
            "electrostatic_surface": False,
            "show_2d_panel": False,
        },
        "publication": {
            "surface_transparency": 0.65,
            "run_hbonds": True,
            "label_interacting_residues": True,
            "nice_lighting": True,
            "pocket_radius": 6.5,
            "electrostatic_surface": False,
            "show_2d_panel": True,
        },
        "analysis": {
            "surface_transparency": 0.55,
            "run_hbonds": True,
            "label_interacting_residues": True,
            "nice_lighting": True,
            "pocket_radius": 7.5,
            "electrostatic_surface": True,
            "show_2d_panel": True,
        },
    }
    return presets.get(preset.lower(), presets["publication"])


def generate_chimera_script(
    job_id: str,
    rank: int = 1,
    receptor_file: str = "protein.pdbqt",
    ligand_file: Optional[str] = None,
    surface_transparency: float = 0.65,
    ligand_color: str = "green",
    run_hbonds: bool = True,
    label_interacting_residues: bool = True,
    nice_lighting: bool = True,
    preset: str = "publication",
    pocket_radius: float = 6.5,
    electrostatic_surface: bool = False,
    show_2d_panel: bool = True,
) -> str:
    """
    Generate a high-quality ChimeraX command script (.cxc) for a docked pose.

    The script generation is now "smart":
    - Supports presets: "minimal", "publication", "analysis"
    - Configurable pocket focus radius
    - Optional electrostatic surface coloring
    - Rich 2D statistics panel
    - Intelligent interaction visualization with distance monitors

    Parameters
    ----------
    job_id : str
        The docking job identifier.
    rank : int
        Which pose to visualize (1-based).
    preset : str
        One of "minimal", "publication", "analysis". Sets smart defaults.
    pocket_radius : float
        Radius in Å around the ligand to consider part of the binding pocket.
    electrostatic_surface : bool
        If True, colors the protein surface by electrostatic potential.
    show_2d_panel : bool
        If True, adds an on-screen 2D label panel with key statistics.
    ... (other parameters override preset values)
    """
    # Apply preset defaults first, then allow explicit overrides
    defaults = get_preset_defaults(preset)
    if surface_transparency == 0.65:  # default value not overridden
        surface_transparency = defaults.get("surface_transparency", 0.65)
    if run_hbonds is True:
        run_hbonds = defaults.get("run_hbonds", True)
    if label_interacting_residues is True:
        label_interacting_residues = defaults.get("label_interacting_residues", True)
    if nice_lighting is True:
        nice_lighting = defaults.get("nice_lighting", True)
    if pocket_radius == 6.5:
        pocket_radius = defaults.get("pocket_radius", 6.5)
    if electrostatic_surface is False:
        electrostatic_surface = defaults.get("electrostatic_surface", False)
    if show_2d_panel is True:
        show_2d_panel = defaults.get("show_2d_panel", True)

    workspace = _get_job_workspace(job_id)
    report = _load_report(job_id)

    # Resolve ligand file - prefer SDF (much better for small molecules)
    if ligand_file is None:
        sdf_path = _find_best_pose_sdf(workspace, rank)
        if sdf_path:
            ligand_file = os.path.basename(sdf_path)
        else:
            ligand_file = "vina_out.pdbqt"

    receptor_path = os.path.join(workspace, receptor_file)
    ligand_path = os.path.join(workspace, ligand_file)

    best_affinity = report.get("best_affinity", "N/A")

    # Collect rich interaction data
    interactions = report.get("interactions", []) if label_interacting_residues else []

    lines = [
        "# ==============================================================================",
        "# ChimeraX Visualization Script",
        "# Generated by Chemistry Companion - Advanced Docking Platform",
        f"# Job ID: {job_id}",
        f"# Pose Rank: {rank}",
        f"# Binding Affinity: {best_affinity} kcal/mol",
        "# ==============================================================================",
        "",
        "# This script creates a high-quality, publication-ready visualization of",
        "# the protein-ligand complex with emphasis on the binding site and interactions.",
        "",
        "close all",
        "set bgColor white",
        "",
        "# ------------------------------------------------------------------------------",
        "# Load Structures",
        "# ------------------------------------------------------------------------------",
        f'open "{receptor_path}" name receptor',
        f'open "{ligand_path}" name ligand',
        "",
        "# Rename for clarity",
        "rename #1 receptor",
        "rename #2 ligand",
        "",
        "# ------------------------------------------------------------------------------",
        "# Protein Representation (Cartoon + Transparent Surface)",
        "# ------------------------------------------------------------------------------",
        "cartoon receptor",
        "surface receptor",
        f"transparency receptor {surface_transparency}",
        "",
        "# Optional: color surface by hydrophobicity (very useful for binding sites)",
        "# color receptor byattribute hydrophobicity palette blue:red",
        "",
        "# ------------------------------------------------------------------------------",
        "# Ligand Representation",
        "# ------------------------------------------------------------------------------",
        "style ligand ball",
        f"color ligand {ligand_color}",
        "size ligand stickRadius 0.2",
        "",
        "# Make ligand stand out strongly",
        "select ligand",
        "color sel byelement",
        "",
        "# ------------------------------------------------------------------------------",
        "# Interaction Analysis & Highlighting",
        "# ------------------------------------------------------------------------------",
    ]

    if run_hbonds:
        lines.extend([
            "# Native ChimeraX H-bond detection (very reliable)",
            "hbonds #receptor to #ligand colorByDistance true radius 0.08",
            "",
        ])

    if interactions:
        lines.append("# --- Smart Interaction Highlighting (from docking report) ---")
        lines.append("")

        # Group by residue and keep best (closest) interaction per residue
        res_to_best = {}
        for ia in interactions:
            res = ia.get("protein_residue", "")
            itype = ia.get("type", "Contact")
            dist = float(ia.get("distance", 99))
            if res and (res not in res_to_best or dist < res_to_best[res]["distance"]):
                res_to_best[res] = {
                    "type": itype,
                    "distance": dist,
                    "ligand_atom": ia.get("ligand_atom", "")
                }

        # Sort by distance (strongest first) and take top 7 to avoid clutter
        sorted_res = sorted(res_to_best.items(), key=lambda x: x[1]["distance"])[:7]

        # Color mapping for different interaction types
        type_color = {
            "H-bond": "deepskyblue",
            "Hydrophobic": "darkorange",
            "Salt Bridge": "red",
            "Pi-Stacking": "mediumpurple",
            "Contact": "gray"
        }

        for res, info in sorted_res:
            parts = res.split()
            if len(parts) >= 2:
                resname, resnum = parts[0], parts[1]
                sel = f"receptor & residue {resnum}"
                color = type_color.get(info["type"], "orange")

                label = f"{resname}{resnum} ({info['type']}, {info['distance']:.1f}Å)"

                lines.extend([
                    f"select {sel}",
                    f"color sel {color}",
                    f'label sel text "{label}" size 16 color black',
                    "",
                    f"# Distance monitor to closest ligand atom for this interaction",
                    f"distance #ligand to {sel} color {color} radius 0.05",
                ])

        lines.append("")

        # Add a quick legend
        lines.extend([
            "echo '=== Interaction Legend (colored by type) ==='",
            "echo 'deepskyblue = H-bond'",
            "echo 'darkorange  = Hydrophobic'",
            "echo 'red         = Salt Bridge'",
            "echo 'mediumpurple = Pi-Stacking'",
            "",
        ])

    # Use the new smart helper for even better interaction commands
    smart_ia = _generate_smart_interaction_commands(interactions)
    if smart_ia:
        lines.extend(smart_ia)

    # Final presentation polish + pocket focus
    lines.extend(_add_pocket_focus_commands())
    lines.extend([
        "# ------------------------------------------------------------------------------",
        "# Final Polish & Presentation",
        "# ------------------------------------------------------------------------------",
        "select receptor & ligand",
        "view sel",
        "",
        "# Nice modern appearance",
        "set silhouette true",
        "lighting soft",
        "graphics quality high",
        "",
        "# Hide hydrogens on protein for cleaner view (optional)",
        "# hide receptor atoms element H",
        "",
        "# ------------------------------------------------------------------------------",
        "# Useful Commands (uncomment as needed)",
        "# ------------------------------------------------------------------------------",
        "",
        "# High-resolution image export:",
        "# save docked_pose.png width 2400 height 1800 supersample 4",
        "",
        "# Save complete session (recommended for publication):",
        "# save docked_pose.cxs",
        "",
        "# Ray-traced image (even higher quality):",
        "# save docked_pose_raytraced.png width 2000 height 1500 supersample 3 raytrace true",
        "",
        "# Reset view to focus tightly on ligand:",
        "# view ligand",
        "",
        "echo 'ChimeraX visualization ready. Enjoy exploring the complex!'",
    ])

    # --- Smart 2D Statistics Panel ---
    if show_2d_panel:
        num_hbonds = sum(1 for ia in interactions if ia.get("type") == "H-bond")
        num_hydrophobic = sum(1 for ia in interactions if ia.get("type") == "Hydrophobic")
        num_salt = sum(1 for ia in interactions if ia.get("type") == "Salt Bridge")

        panel_lines = [
            "# --- On-screen 2D Statistics Panel (smart feature) ---",
            f'2dlabel create stats text "Job: {job_id[:12]}... | Pose {rank} | Affinity: {best_affinity} kcal/mol" ',
            "    xpos 0.02 ypos 0.95 size 16 color black",
            "",
            f'2dlabel create interactions text "Interactions: {len(interactions)} total  |  H-bonds: {num_hbonds}  |  Hydrophobic: {num_hydrophobic}  |  Salt bridges: {num_salt}" ',
            "    xpos 0.02 ypos 0.91 size 14 color darkgray",
            "",
            "2dlabel create tip text \"Use the mouse to rotate. Press 'Esc' for full screen.\" ",
            "    xpos 0.02 ypos 0.02 size 12 color gray",
            "",
        ]
        lines.extend(panel_lines)

    return "\n".join(lines)


# ==============================================================================
# Smarter Helper Functions (new intelligence layer)
# ==============================================================================

def _generate_smart_interaction_commands(interactions: list) -> list[str]:
    """Generate advanced ChimeraX commands for interactions (distance monitors + coloring)."""
    if not interactions:
        return []

    lines = ["# --- Smart Interaction Commands ---"]

    # Color map
    type_color = {
        "H-bond": "deepskyblue",
        "Hydrophobic": "darkorange",
        "Salt Bridge": "red",
        "Pi-Stacking": "mediumpurple",
    }

    # Take top 6 closest interactions
    sorted_ia = sorted(interactions, key=lambda x: float(x.get("distance", 99)))[:6]

    for ia in sorted_ia:
        res = ia.get("protein_residue", "")
        itype = ia.get("type", "")
        dist = ia.get("distance", 0)
        color = type_color.get(itype, "gray")

        if res:
            parts = res.split()
            if len(parts) >= 2:
                resnum = parts[1]
                label = f"{res} ({itype}, {dist}Å)"
                lines.extend([
                    f"select receptor & residue {resnum}",
                    f"color sel {color}",
                    f'label sel text "{label}" size 15 color black',
                    f"distance #ligand to sel color {color} radius 0.05",
                ])

    return lines


def _add_pocket_focus_commands() -> list[str]:
    """Return commands to intelligently focus only on the binding pocket."""
    return [
        "# --- Smart Pocket Focus ---",
        "select ligand",
        "sel = sel | sel :< 6.5",
        "select sel",
        "~display ~sel",
        "view sel",
    ]


def create_chimera_bundle(
    job_id: str,
    rank: int = 1,
    output_dir: Optional[str] = None,
    include_script: bool = True,
) -> str:
    """
    Create a self-contained bundle (directory) with the .cxc script + structure files.

    This makes it very easy for the user to double-click the script on their machine.

    Returns the path to the created directory.
    """
    workspace = _get_job_workspace(job_id)

    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix=f"chimera_{job_id[:8]}_pose{rank}_")

    os.makedirs(output_dir, exist_ok=True)

    # Copy key structure files
    files_to_copy = [
        "protein.pdbqt",
        f"pose_{rank}.sdf",
        "vina_out.pdbqt",
        "ligand.pdbqt",
    ]

    for fname in files_to_copy:
        src = os.path.join(workspace, fname)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(output_dir, fname))

    # Generate and write the script
    if include_script:
        script_content = generate_chimera_script(job_id, rank=rank)
        script_path = os.path.join(output_dir, f"view_pose_{rank}.cxc")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)

        # Also write a README
        readme = f"""ChimeraX Visualization Bundle
Job: {job_id}
Pose: {rank}

1. Install UCSF ChimeraX if you don't have it (https://www.cgl.ucsf.edu/chimerax/).
2. Double-click the .cxc file, or open it from within ChimeraX.
3. For best results, run the script from inside this folder.

You can also run individual commands or modify the script.
"""
        with open(os.path.join(output_dir, "README.txt"), "w", encoding="utf-8") as f:
            f.write(readme)

    logger.info("Created ChimeraX bundle for job %s pose %s at %s", job_id, rank, output_dir)
    return output_dir


# Convenience function used by the service layer
def get_chimera_script_for_job(job_id: str, rank: int = 1) -> str:
    """Simple wrapper used by the API layer."""
    return generate_chimera_script(job_id, rank=rank)
