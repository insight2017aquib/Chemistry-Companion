"""
services/docking_workspace_service.py
=====================================
Service layer for the complete docking workflow.
Checks HAS_DOCKING before calling any Vina / OpenBabel code.
"""

import os
import uuid
import json
import logging
from typing import Dict, Any

from docking_workflow import HAS_DOCKING

logger = logging.getLogger(__name__)

WORKSPACE_DIR = os.path.join(os.getcwd(), "outputs", "docking_workspace")

_UNAVAILABLE_MSG = (
    "Docking features require additional dependencies (vina, meeko, openbabel). "
    "Install them with: conda install -c conda-forge vina autodock-vina openbabel && pip install meeko"
)


def _write_text(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content or "")


def _write_json(path: str, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _require_text(label: str, content: str) -> None:
    if not content or not content.strip():
        raise ValueError(f"{label} cannot be empty.")


class DockingWorkspaceService:
    """
    Service layer for the complete docking workflow.
    Manages job states, file persistence, and orchestrates docking_workflow package.
    """

    @staticmethod
    def is_available() -> bool:
        """Check whether the docking backend is ready."""
        return HAS_DOCKING

    @staticmethod
    def unavailable_message() -> str:
        return _UNAVAILABLE_MSG

    @staticmethod
    def get_workspace(job_id: str) -> str:
        path = os.path.join(WORKSPACE_DIR, job_id)
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def create_job() -> str:
        job_id = str(uuid.uuid4())
        DockingWorkspaceService.get_workspace(job_id)
        logger.info("Created docking workspace job %s.", job_id)
        return job_id

    @staticmethod
    def prepare_protein(pdb_text: str, remove_water: bool = True, add_charges: bool = True) -> str:
        if not HAS_DOCKING:
            raise RuntimeError(_UNAVAILABLE_MSG)
        from docking_workflow import prepare_protein

        _require_text("Protein PDB text", pdb_text)
        logger.info(
            "Preparing receptor protein: input_length=%d, remove_water=%s, add_charges=%s",
            len(pdb_text), remove_water, add_charges
        )
        try:
            pdbqt = prepare_protein(pdb_text, remove_water, add_charges)
            logger.info("Protein preparation completed: pdbqt_length=%d.", len(pdbqt))
            return pdbqt
        except Exception:
            logger.exception("Protein preparation failed.")
            raise

    @staticmethod
    def calculate_gridbox(pdbqt_text: str):
        if not HAS_DOCKING:
            raise RuntimeError(_UNAVAILABLE_MSG)
        from docking_workflow import auto_gridbox

        _require_text("Receptor PDBQT text", pdbqt_text)
        logger.info("Calculating docking grid box from receptor PDBQT: length=%d.", len(pdbqt_text))
        try:
            config = auto_gridbox(pdbqt_text)
            logger.info(
                "Grid box calculated: center=(%.3f, %.3f, %.3f), size=(%.3f, %.3f, %.3f).",
                config.center_x, config.center_y, config.center_z,
                config.size_x, config.size_y, config.size_z
            )
            return config
        except Exception:
            logger.exception("Grid box calculation failed.")
            raise

    @staticmethod
    def run_docking(
        job_id: str,
        protein_pdbqt: str,
        ligand_pdbqt: str,
        center_x: float, center_y: float, center_z: float,
        size_x: float, size_y: float, size_z: float,
        exhaustiveness: int = 8,
        num_modes: int = 9
    ) -> Dict[str, Any]:
        """Runs Vina, maps interactions, builds report, saves outputs."""
        if not HAS_DOCKING:
            raise RuntimeError(_UNAVAILABLE_MSG)

        from docking_workflow import run_vina, parse_vina_output, map_interactions, build_docking_report

        workspace = DockingWorkspaceService.get_workspace(job_id)
        logger.info("Starting docking job %s in %s.", job_id, workspace)

        _require_text("Receptor PDBQT text", protein_pdbqt)
        _require_text("Ligand PDBQT text", ligand_pdbqt)

        config = {
            "center": {"x": center_x, "y": center_y, "z": center_z},
            "size": {"x": size_x, "y": size_y, "z": size_z},
            "exhaustiveness": exhaustiveness,
            "num_modes": num_modes,
        }
        _write_text(os.path.join(workspace, "protein.pdbqt"), protein_pdbqt)
        _write_text(os.path.join(workspace, "ligand.pdbqt"), ligand_pdbqt)
        _write_json(os.path.join(workspace, "config.json"), config)

        stage = "vina execution"
        try:
            result = run_vina(
                protein_pdbqt, ligand_pdbqt,
                center_x, center_y, center_z,
                size_x, size_y, size_z,
                exhaustiveness, num_modes
            )

            out_path = os.path.join(workspace, "vina_out.pdbqt")
            log_path = os.path.join(workspace, "vina.log")
            _write_text(out_path, result.pdbqt_output)
            _write_text(log_path, result.log_text)
            logger.info("Docking job %s Vina output saved to %s.", job_id, out_path)

            stage = "pose parsing"
            poses = parse_vina_output(result.pdbqt_output)
            if not poses:
                raise RuntimeError("Vina completed but no parseable poses were found in the output.")
            logger.info("Docking job %s parsed %d pose(s).", job_id, len(poses))

            stage = "interaction mapping"
            best_interactions = []
            try:
                best_interactions = map_interactions(protein_pdbqt, poses[0].pdbqt_block)
            except Exception:
                logger.exception("Interaction mapping failed for docking job %s; continuing with no interactions.", job_id)

            stage = "report building"
            report = build_docking_report(poses, best_interactions)
            report["artifacts"] = {
                "workspace": workspace,
                "protein_pdbqt": os.path.join(workspace, "protein.pdbqt"),
                "ligand_pdbqt": os.path.join(workspace, "ligand.pdbqt"),
                "vina_output": out_path,
                "vina_log": log_path,
            }
            report_path = os.path.join(workspace, "report.json")
            _write_json(report_path, report)
            logger.info(
                "Docking job %s completed: poses=%d, best_affinity=%s.",
                job_id, report.get("num_poses"), report.get("best_affinity")
            )

            return report
        except Exception as exc:
            logger.exception("Docking job %s failed during %s.", job_id, stage)
            raise RuntimeError(f"Docking job {job_id} failed during {stage}: {exc}") from exc

    @staticmethod
    def get_pose(job_id: str, rank: int) -> Dict[str, Any]:
        if not HAS_DOCKING:
            raise RuntimeError(_UNAVAILABLE_MSG)
        from docking_workflow import parse_vina_output
        workspace = DockingWorkspaceService.get_workspace(job_id)
        out_path = os.path.join(workspace, "vina_out.pdbqt")
        if not os.path.exists(out_path):
            raise FileNotFoundError(f"No docking output found for job {job_id}")
        with open(out_path, encoding="utf-8") as f:
            poses = parse_vina_output(f.read())
        for p in poses:
            if p.rank == rank:
                return {"rank": p.rank, "affinity": p.affinity_kcal, "pdbqt": p.pdbqt_block}
        raise ValueError(f"Pose rank {rank} not found in job {job_id}")

    @staticmethod
    def get_interactions(job_id: str, rank: int):
        if not HAS_DOCKING:
            raise RuntimeError(_UNAVAILABLE_MSG)
        from docking_workflow import parse_vina_output, map_interactions
        workspace = DockingWorkspaceService.get_workspace(job_id)
        out_path = os.path.join(workspace, "vina_out.pdbqt")
        if not os.path.exists(out_path):
            raise FileNotFoundError(f"No docking output found for job {job_id}")
        with open(out_path, encoding="utf-8") as f:
            poses = parse_vina_output(f.read())
        protein_path = os.path.join(workspace, "protein.pdbqt")
        if not os.path.exists(protein_path):
            logger.warning("No saved protein.pdbqt found for docking job %s; cannot map interactions.", job_id)
            return []
        with open(protein_path, encoding="utf-8") as f:
            protein_pdbqt = f.read()
        for p in poses:
            if p.rank == rank:
                return map_interactions(protein_pdbqt, p.pdbqt_block)
        return []
