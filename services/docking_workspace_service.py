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
from dataclasses import asdict
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session

from core.paths import docking_workspace_root
from database.models import DockingJob as DBDockingJob
from docking_workflow import HAS_DOCKING

logger = logging.getLogger(__name__)

WORKSPACE_DIR = str(docking_workspace_root())

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
        """Legacy preparation method (kept for backward compatibility)."""
        if not HAS_DOCKING:
            raise RuntimeError(_UNAVAILABLE_MSG)
        from docking_workflow import prepare_protein

        _require_text("Protein PDB text", pdb_text)
        logger.info(
            "Preparing receptor protein (legacy): input_length=%d, remove_water=%s, add_charges=%s",
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
    def prepare_receptor_with_options(pdb_text: str, options_dict: Dict[str, Any]) -> str:
        """
        Phase 4/5: New recommended preparation method that respects
        cofactor and metal handling decisions.
        """
        if not HAS_DOCKING:
            raise RuntimeError(_UNAVAILABLE_MSG)

        from docking_workflow.protein_preparation import (
            prepare_receptor as _prepare_receptor,
            PreparationOptions
        )

        _require_text("Protein PDB text", pdb_text)

        # Convert dict to dataclass (with safe defaults)
        options = PreparationOptions(
            remove_water=options_dict.get("remove_water", True),
            add_charges=options_dict.get("add_charges", True),
            keep_cofactors=options_dict.get("keep_cofactors", False),
            keep_metals=options_dict.get("keep_metals", False),
            keep_active_site_waters=options_dict.get("keep_active_site_waters", False),
            remove_bulk_waters=options_dict.get("remove_bulk_waters", True),
            remove_ligands=options_dict.get("remove_ligands", True),
            run_protonation=options_dict.get("run_protonation", False),
            ph=options_dict.get("ph", 7.4),
        )

        logger.info("Preparing receptor with rich options: %s", options)

        try:
            pdbqt = _prepare_receptor(pdb_text, options)
            logger.info("Advanced receptor preparation completed: pdbqt_length=%d.", len(pdbqt))
            return pdbqt
        except Exception:
            logger.exception("Advanced receptor preparation failed.")
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
        num_modes: int = 9,
        scoring_function: str = "vina",
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Runs Vina, maps interactions, builds report, saves outputs."""
        if not HAS_DOCKING:
            raise RuntimeError(_UNAVAILABLE_MSG)

        from docking_workflow import run_vina, parse_vina_output, map_interactions, build_docking_report
        from docking_workflow.protein_preparation import clean_rigid_receptor_pdbqt

        workspace = DockingWorkspaceService.get_workspace(job_id)
        logger.info("Starting docking job %s in %s.", job_id, workspace)

        _require_text("Receptor PDBQT text", protein_pdbqt)
        _require_text("Ligand PDBQT text", ligand_pdbqt)

        # Clean the receptor PDBQT to ensure no ROOT/BRANCH tags are present 
        # (important if user uploaded a raw PDBQT directly)
        protein_pdbqt, _ = clean_rigid_receptor_pdbqt(protein_pdbqt)

        config = {
            "center": {"x": center_x, "y": center_y, "z": center_z},
            "size": {"x": size_x, "y": size_y, "z": size_z},
            "exhaustiveness": exhaustiveness,
            "num_modes": num_modes,
            "scoring_function": scoring_function,
            "seed": seed,
        }
        _write_text(os.path.join(workspace, "protein.pdbqt"), protein_pdbqt)
        _write_text(os.path.join(workspace, "ligand.pdbqt"), ligand_pdbqt)
        _write_json(os.path.join(workspace, "config.json"), config)

        stage = "vina execution"
        logger.info(
            "INVOKING VINA now for job=%s: center=(%.3f,%.3f,%.3f) size=(%.1f,%.1f,%.1f) exh=%d modes=%d scoring=%s seed=%s",
            job_id, center_x, center_y, center_z, size_x, size_y, size_z, exhaustiveness, num_modes,
            scoring_function, seed
        )
        try:
            result = run_vina(
                protein_pdbqt, ligand_pdbqt,
                center_x, center_y, center_z,
                size_x, size_y, size_z,
                exhaustiveness, num_modes,
                scoring_function=scoring_function,
                seed=seed,
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

            stage = "saving SDF poses"
            for p in poses:
                sdf_data = ""
                try:
                    from core.openbabel_utils import convert_format
                    sdf_data = convert_format(p.pdbqt_block, "pdbqt", "sdf")
                except Exception as e:
                    logger.debug("OpenBabel SDF conversion failed/missing: %s, trying RDKit fallback", e)
                    try:
                        from rdkit import Chem
                        mol = Chem.MolFromPDBBlock(p.pdbqt_block, removeHs=False)
                        if mol:
                            sdf_data = Chem.MolToMolBlock(mol)
                    except Exception as rdkit_err:
                        logger.warning("RDKit fallback SDF conversion failed: %s", rdkit_err)

                if sdf_data:
                    _write_text(os.path.join(workspace, f"pose_{p.rank}.sdf"), sdf_data)
                else:
                    logger.warning("Could not convert pose %s to SDF.", p.rank)

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
                data = {"rank": p.rank, "affinity": p.affinity_kcal, "pdbqt": p.pdbqt_block}
                sdf_data = ""
                try:
                    from core.openbabel_utils import convert_format
                    sdf_data = convert_format(p.pdbqt_block, "pdbqt", "sdf")
                except Exception as e:
                    try:
                        from rdkit import Chem
                        mol = Chem.MolFromPDBBlock(p.pdbqt_block, removeHs=False)
                        if mol:
                            sdf_data = Chem.MolToMolBlock(mol)
                    except Exception:
                        pass
                if sdf_data:
                    data["sdf"] = sdf_data
                return data
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

    # ── Pose Rescoring / Consensus (Advanced Docking P5) ────────────────

    @staticmethod
    def rescore_pose(job_id: str, rank: int = 1, scoring_function: str = "vinardo") -> Dict[str, Any]:
        """Re-score a stored pose with a second scoring function and return a
        consensus view (original Vina affinity + rescore)."""
        if not HAS_DOCKING:
            raise RuntimeError(_UNAVAILABLE_MSG)

        from docking_workflow import parse_vina_output
        from docking_workflow.vina_runner import rescore_pose as _rescore

        workspace = DockingWorkspaceService.get_workspace(job_id)
        out_path = os.path.join(workspace, "vina_out.pdbqt")
        protein_path = os.path.join(workspace, "protein.pdbqt")
        config_path = os.path.join(workspace, "config.json")
        if not os.path.exists(out_path) or not os.path.exists(protein_path):
            raise FileNotFoundError(f"No docking output/receptor found for job {job_id}")

        with open(out_path, encoding="utf-8") as f:
            poses = parse_vina_output(f.read())
        with open(protein_path, encoding="utf-8") as f:
            protein_pdbqt = f.read()
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"No grid config found for job {job_id}")
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        pose = next((p for p in poses if p.rank == rank), None)
        if pose is None:
            raise ValueError(f"Pose rank {rank} not found in job {job_id}")

        c, s = config["center"], config["size"]
        rescored = _rescore(
            protein_pdbqt, pose.pdbqt_block,
            c["x"], c["y"], c["z"], s["x"], s["y"], s["z"],
            scoring_function=scoring_function,
        )
        return {
            "job_id": job_id,
            "rank": rank,
            "original_affinity": pose.affinity_kcal,
            "original_scoring": config.get("scoring_function", "vina"),
            "rescore_affinity": rescored,
            "rescore_scoring": scoring_function,
            "available": rescored is not None,
            "note": None if rescored is not None else (
                "Rescoring requires the standalone Vina CLI; it is unavailable in this environment."
            ),
        }

    # ── Redocking Validation (Advanced Docking P1) ──────────────────────

    @staticmethod
    def redock_validation(
        pdb_text: str,
        resname: Optional[str] = None,
        chain: Optional[str] = None,
        resnum: Optional[int] = None,
        exhaustiveness: int = 8,
        num_modes: int = 9,
        scoring_function: str = "vina",
        seed: Optional[int] = None,
        remove_water: bool = True,
    ) -> Dict[str, Any]:
        """Cognate-ligand redocking validation: re-dock the co-crystal ligand and
        report RMSD to the crystallographic pose (pass < 2 Å)."""
        if not HAS_DOCKING:
            raise RuntimeError(_UNAVAILABLE_MSG)

        from docking_workflow.redock_validation import redock_validate

        _require_text("Protein PDB text", pdb_text)
        result = redock_validate(
            pdb_text, resname=resname, chain=chain, resnum=resnum,
            exhaustiveness=exhaustiveness, num_modes=num_modes,
            scoring_function=scoring_function, seed=seed, remove_water=remove_water,
        )
        return result.to_dict()

    # ── Advanced Ligand Preparation (Advanced Docking P2) ────────────────

    @staticmethod
    def prepare_ligand_states(smiles: str, options: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Prepare one or more docking-ready ligand states (Meeko-first, enumeration
        opt-in). Returns a list of state dicts (label, smiles, pdbqt, method)."""
        if not HAS_DOCKING:
            raise RuntimeError(_UNAVAILABLE_MSG)

        from core.ligand_prep import prepare_ligand_states as _prepare

        _require_text("Ligand SMILES", smiles)
        opts = options or {}
        states = _prepare(
            smiles,
            ph=opts.get("ph"),
            enumerate_protonation=opts.get("enumerate_protonation", False),
            enumerate_tautomers=opts.get("enumerate_tautomers", False),
            enumerate_stereo=opts.get("enumerate_stereo", False),
            n_conformers=opts.get("n_conformers", 1),
            prefer_meeko=opts.get("prefer_meeko", True),
        )
        return [s.to_dict() for s in states]

    # ── Batch / Ensemble Docking (Advanced Docking P4) ───────────────────

    @staticmethod
    def run_batch_docking(
        receptor_pdbqt: str,
        ligands: List[Dict[str, Any]],
        center_x: float, center_y: float, center_z: float,
        size_x: float, size_y: float, size_z: float,
        exhaustiveness: int = 8,
        num_modes: int = 9,
        scoring_function: str = "vina",
        seed: Optional[int] = None,
        ligand_prep_options: Optional[Dict[str, Any]] = None,
        reference_interactions: Optional[List[Dict[str, Any]]] = None,
        batch_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Dock a set of ligands (e.g. an SAR series from a CSV) against one receptor
        and grid, returning a ranked comparison table.

        For each ligand the best-scoring prepared state is kept. Ligand efficiency
        (-affinity / heavy-atom count) and — when a reference interaction fingerprint
        is supplied — interaction-fingerprint similarity are reported per ligand.
        """
        if not HAS_DOCKING:
            raise RuntimeError(_UNAVAILABLE_MSG)

        from rdkit import Chem
        from core.ligand_prep import prepare_ligand_states
        from docking_workflow.interaction_fingerprint import compare_interactions

        _require_text("Receptor PDBQT text", receptor_pdbqt)
        if not ligands:
            raise ValueError("No ligands provided for batch docking.")

        batch_id = batch_id or str(uuid.uuid4())
        batch_dir = os.path.join(WORKSPACE_DIR, f"batch_{batch_id}")
        os.makedirs(batch_dir, exist_ok=True)
        prep_opts = ligand_prep_options or {}

        results: List[Dict[str, Any]] = []
        for idx, entry in enumerate(ligands):
            smiles = (entry.get("smiles") or "").strip()
            name = entry.get("name") or f"cmpd_{idx + 1}"
            if not smiles:
                results.append({"name": name, "smiles": smiles, "status": "error",
                                "error": "Empty SMILES"})
                continue

            try:
                heavy = 0
                mol = Chem.MolFromSmiles(smiles)
                if mol is not None:
                    heavy = mol.GetNumHeavyAtoms()

                states = prepare_ligand_states(smiles, **prep_opts)
                best: Optional[Dict[str, Any]] = None
                for state in states:
                    job_id = DockingWorkspaceService.create_job()
                    report = DockingWorkspaceService.run_docking(
                        job_id, receptor_pdbqt, state.pdbqt,
                        center_x, center_y, center_z, size_x, size_y, size_z,
                        exhaustiveness, num_modes,
                        scoring_function=scoring_function, seed=seed,
                    )
                    aff = report.get("best_affinity")
                    if aff is None:
                        continue
                    if best is None or aff < best["best_affinity"]:
                        best = {
                            "job_id": job_id,
                            "best_affinity": aff,
                            "state_label": state.label,
                            "state_smiles": state.smiles,
                            "interactions": report.get("interactions", []),
                        }

                if best is None:
                    results.append({"name": name, "smiles": smiles, "status": "error",
                                    "error": "No scored poses produced"})
                    continue

                aff = best["best_affinity"]
                le = round(-aff / heavy, 3) if heavy else None
                fp_similarity = None
                if reference_interactions is not None:
                    fp_similarity = compare_interactions(
                        reference_interactions, best["interactions"]
                    ).similarity

                results.append({
                    "name": name,
                    "smiles": smiles,
                    "status": "completed",
                    "job_id": best["job_id"],
                    "best_affinity": aff,
                    "pkd": round(-aff / 1.364, 2) if aff < 0 else None,
                    "ligand_efficiency": le,
                    "heavy_atoms": heavy,
                    "state_label": best["state_label"],
                    "fingerprint_similarity": (round(fp_similarity, 3)
                                               if fp_similarity is not None else None),
                })
            except Exception as exc:  # noqa: BLE001
                logger.exception("Batch docking failed for ligand %s", name)
                results.append({"name": name, "smiles": smiles, "status": "error",
                                "error": str(exc)})

        # Rank completed ligands by affinity (most negative = best).
        completed = [r for r in results if r.get("status") == "completed"]
        completed.sort(key=lambda r: r["best_affinity"])
        for rank, r in enumerate(completed, start=1):
            r["rank"] = rank

        summary = {
            "batch_id": batch_id,
            "num_ligands": len(ligands),
            "num_completed": len(completed),
            "num_failed": len(ligands) - len(completed),
            "grid": {"center": {"x": center_x, "y": center_y, "z": center_z},
                     "size": {"x": size_x, "y": size_y, "z": size_z}},
            "scoring_function": scoring_function,
            "results": results,
            "ranking": completed,
        }
        _write_json(os.path.join(batch_dir, "batch_report.json"), summary)
        logger.info("Batch docking %s complete: %d/%d succeeded.",
                    batch_id, len(completed), len(ligands))
        return summary

    @staticmethod
    def get_batch_report(batch_id: str) -> Dict[str, Any]:
        """Load a previously computed batch docking summary."""
        batch_dir = os.path.join(WORKSPACE_DIR, f"batch_{batch_id}")
        report_path = os.path.join(batch_dir, "batch_report.json")
        if not os.path.exists(report_path):
            raise FileNotFoundError(f"No batch report found for batch {batch_id}")
        with open(report_path, encoding="utf-8") as f:
            return json.load(f)

    # ── Phase 1 B: DockingJob DB Persistence ─────────────────────────────

    def save_docking_job(
        self,
        db: Session,
        job_id: str,
        report: Dict[str, Any],
        grid_config: Optional[Dict[str, Any]] = None,
        receptor_name: Optional[str] = None,
        ligand_smiles: Optional[str] = None,
        ligand_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> dict:
        """Persist lightweight metadata for a completed docking job."""
        workspace = self.get_workspace(job_id)
        report_path = os.path.join(workspace, "report.json")

        best_affinity = report.get("best_affinity")
        num_poses = report.get("num_poses", 0)

        existing = db.query(DBDockingJob).filter(DBDockingJob.id == job_id).first()
        if existing:
            existing.name = ligand_name or existing.name or f"Docking {job_id[:8]}"
            if receptor_name is not None:
                existing.receptor_name = receptor_name
            if ligand_smiles is not None:
                existing.ligand_smiles = ligand_smiles
            if ligand_name is not None:
                existing.ligand_name = ligand_name
            g = grid_config or report.get("grid_config")
            if g:
                existing.grid = g
            if best_affinity is not None:
                existing.best_affinity = str(best_affinity)
            existing.num_poses = num_poses
            existing.status = "completed"
            if workspace:
                existing.workspace_path = workspace
            existing.report_path = report_path
            if tags:
                existing.tags = tags
            db.commit()
            db.refresh(existing)
            return existing.to_dict()

        entry = DBDockingJob(
            id=job_id,
            name=ligand_name or f"Docking {job_id[:8]}",
            receptor_name=receptor_name,
            ligand_smiles=ligand_smiles,
            ligand_name=ligand_name,
            grid=grid_config or report.get("grid_config"),
            best_affinity=str(best_affinity) if best_affinity is not None else None,
            num_poses=num_poses,
            status="completed",
            workspace_path=workspace,
            report_path=report_path,
            tags=tags or [],
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry.to_dict()

    def get_docking_job(self, db: Session, job_id: str) -> Optional[dict]:
        """Retrieve a DockingJob DB record by id."""
        row = db.query(DBDockingJob).filter(DBDockingJob.id == job_id).first()
        return row.to_dict() if row else None

    def list_docking_jobs(
        self,
        db: Session,
        limit: int = 50,
        offset: int = 0,
    ) -> List[dict]:
        """List recent docking jobs (most recent first)."""
        q = db.query(DBDockingJob).order_by(DBDockingJob.created_at.desc())
        rows = q.offset(offset).limit(limit).all()
        return [row.to_dict() for row in rows]

    # ── ChimeraX Integration (Phase 2 first slice) ──────────────────────

    def get_chimera_script(self, job_id: str, rank: int = 1) -> str:
        """Return the content of a high-quality .cxc script for a pose."""
        if not HAS_DOCKING:
            raise RuntimeError(_UNAVAILABLE_MSG)

        from docking_workflow.chimera_exporter import get_chimera_script_for_job
        return get_chimera_script_for_job(job_id, rank=rank)

    def create_chimera_bundle(self, job_id: str, rank: int = 1, output_dir: Optional[str] = None) -> str:
        """Create a folder containing the .cxc script + structure files. Returns the folder path."""
        if not HAS_DOCKING:
            raise RuntimeError(_UNAVAILABLE_MSG)

        from docking_workflow.chimera_exporter import create_chimera_bundle as _create_bundle
        return _create_bundle(job_id, rank=rank, output_dir=output_dir)

    def launch_chimera(self, job_id: str, rank: int = 1) -> dict:
        """
        Attempt to launch ChimeraX with the generated script for a pose.
        Returns status information.
        """
        from core.external_tools import get_chimera_executable, is_chimera_available
        import subprocess

        exe = get_chimera_executable()
        if not exe or not is_chimera_available():
            return {
                "success": False,
                "error": "ChimeraX executable not configured or not found.",
                "executable": exe
            }

        try:
            script = self.get_chimera_script(job_id, rank=rank)
            workspace = self.get_workspace(job_id)

            # Write a temporary script in the workspace and launch it
            script_path = os.path.join(workspace, f"chimera_view_pose_{rank}.cxc")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script)

            # Launch ChimeraX with the script
            subprocess.Popen([exe, script_path], cwd=workspace)
            return {
                "success": True,
                "message": f"Launched ChimeraX with pose {rank}",
                "script_path": script_path
            }
        except Exception as e:
            logger.exception("Failed to launch ChimeraX")
            return {
                "success": False,
                "error": str(e)
            }

    # ── Pre-docking Protein Analysis (Advanced Docking Phase 1) ──────────

    @staticmethod
    def analyze_protein(pdb_text: str) -> Dict[str, Any]:
        """
        Legacy entry point (kept for full backward compatibility).
        Returns the simpler ProteinAnalysis format.
        """
        if not HAS_DOCKING:
            raise RuntimeError(_UNAVAILABLE_MSG)

        from docking_workflow import analyze_protein as _analyze

        _require_text("Protein PDB text", pdb_text)
        logger.info("Running pre-docking protein analysis (legacy) (length=%d).", len(pdb_text))
        try:
            result = _analyze(pdb_text)
            return result.to_dict()
        except Exception:
            logger.exception("Protein analysis failed.")
            raise

    @staticmethod
    def analyze_receptor(pdb_text: str) -> Dict[str, Any]:
        """
        NEW recommended entry point for rich receptor analysis (Phase 1+).
        """
        if not HAS_DOCKING:
            raise RuntimeError(_UNAVAILABLE_MSG)

        from docking_workflow.protein_analysis import analyze_receptor as _analyze_receptor

        _require_text("Protein PDB text", pdb_text)
        logger.info("Running rich receptor analysis (length=%d).", len(pdb_text))
        try:
            result = _analyze_receptor(pdb_text)
            return result.to_dict()
        except Exception:
            logger.exception("Receptor analysis failed.")
            raise

    @staticmethod
    def detect_ligand_binding_sites(pdb_text: str) -> List[Dict[str, Any]]:
        """
        Phase 3A: Ligand-based binding site detection.
        """
        if not HAS_DOCKING:
            raise RuntimeError(_UNAVAILABLE_MSG)

        from docking_workflow.protein_analysis import (
            analyze_receptor as _analyze_receptor,
            detect_ligand_binding_sites as _detect_sites
        )

        _require_text("Protein PDB text", pdb_text)

        try:
            report = _analyze_receptor(pdb_text)
            sites = _detect_sites(pdb_text, report)
            return [asdict(s) for s in sites] if sites else []
        except Exception:
            logger.exception("Ligand binding site detection failed.")
            return []

    @staticmethod
    def detect_pockets(pdb_text: str) -> Dict[str, Any]:
        """
        Phase 3B: Pocket-based binding site detection (when no ligand is present).
        """
        if not HAS_DOCKING:
            raise RuntimeError(_UNAVAILABLE_MSG)

        from docking_workflow.pocket_detection import (
            detect_pockets as _detect_pockets,
            pockets_to_suggestions
        )

        _require_text("Protein PDB text", pdb_text)

        try:
            pockets = _detect_pockets(pdb_text)
            suggestions = pockets_to_suggestions(pockets)

            return {
                "pockets": [p.to_dict() for p in pockets],
                "suggestions": suggestions,
                "count": len(pockets),
                "tool_used": "fpocket" if pockets else None,
                "message": None if pockets else "fpocket not available or no pockets detected."
            }
        except Exception as e:
            logger.exception("Pocket detection failed.")
            return {
                "pockets": [],
                "suggestions": [],
                "count": 0,
                "tool_used": None,
                "message": f"Pocket detection failed: {str(e)}"
            }

    @staticmethod
    def classify_waters(pdb_text: str) -> Dict[str, Any]:
        """
        Phase 6: Water classification and recommendations.
        """
        if not HAS_DOCKING:
            raise RuntimeError(_UNAVAILABLE_MSG)

        from docking_workflow.water_analysis import classify_waters as _classify_waters, get_water_summary
        from docking_workflow.protein_analysis import analyze_receptor as _analyze_receptor

        _require_text("Protein PDB text", pdb_text)

        try:
            report = _analyze_receptor(pdb_text)
            waters = _classify_waters(pdb_text, report)
            summary = get_water_summary(waters)

            return {
                "waters": [asdict(w) for w in waters],
                "summary": summary,
                "total": len(waters)
            }
        except Exception as e:
            logger.exception("Water classification failed.")
            return {
                "waters": [],
                "summary": {},
                "total": 0,
                "error": str(e)
            }

    @staticmethod
    def protonate_receptor(pdb_text: str, ph: float = 7.4) -> str:
        """
        Phase 7: Standalone protonation step using PDB2PQR + PropKa.
        """
        if not HAS_DOCKING:
            raise RuntimeError(_UNAVAILABLE_MSG)

        from docking_workflow.protonation import protonate_receptor as _protonate

        _require_text("Protein PDB text", pdb_text)

        try:
            return _protonate(pdb_text, ph=ph)
        except Exception:
            logger.exception("Standalone protonation failed.")
            raise

    @staticmethod
    def get_quality_assessment(pdb_text: str) -> Dict[str, Any]:
        """
        Phase 8: Dedicated quality scoring for a receptor.
        Returns detailed breakdown and overall score.
        """
        if not HAS_DOCKING:
            raise RuntimeError(_UNAVAILABLE_MSG)

        from docking_workflow.quality_scorer import compute_quality_score
        from docking_workflow.protein_analysis import analyze_receptor as _analyze_receptor

        _require_text("Protein PDB text", pdb_text)

        try:
            report = _analyze_receptor(pdb_text)
            assessment = compute_quality_score(report)
            return {
                "score": assessment.score,
                "label": assessment.label,
                "breakdown": assessment.breakdown,
                "notes": assessment.notes
            }
        except Exception:
            logger.exception("Quality assessment failed.")
            raise

    # ── AI-Powered Chain Recommendation (25-year expert docking scientist) ─
    @staticmethod
    def get_ai_chain_recommendation(
        analysis_dict: Dict[str, Any],
        ligand_smiles: Optional[str] = None,
        target_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Use the configured LLM (as a 25-year drug discovery docking expert) to recommend
        the biologically most relevant chain(s) for docking.

        This is the "AI kicks in" feature for real multi-chain drug targets (e.g. 4duh class).
        It receives the rich output from analyze_protein and optional ligand/target context.
        """
        if not HAS_DOCKING:
            raise RuntimeError(_UNAVAILABLE_MSG)

        # Build a high-signal prompt that a real 25-year practitioner would respect
        prompt = DockingWorkspaceService._build_ai_chain_prompt(analysis_dict, ligand_smiles, target_name)

        raw_response = None
        last_error = None

        # Prefer the modern robust LLM system (supports Groq + fallbacks by default)
        try:
            from core.llm_utils import _resolve_provider_chain, _try_provider_with_retries

            chain = _resolve_provider_chain()
            if chain:
                # Use the first (primary) provider from the modern chain (Groq by default for most users)
                prov = chain[0]
                text, err_kind, err_detail = _try_provider_with_retries(
                    provider=prov["provider"],
                    api_key=prov["api_key"],
                    model=prov["model"],
                    prompt=prompt,
                    max_retries=2,
                )
                if text:
                    raw_response = text
                else:
                    last_error = f"{prov['provider']}: {err_detail or err_kind}"
            else:
                last_error = "No LLM providers with API keys configured in modern system"
        except Exception as e:
            last_error = f"Modern LLM system error: {e}"

        # Fallback to legacy client only if modern system completely failed
        if raw_response is None:
            try:
                from services.llm_service import get_llm_client
                client = get_llm_client()
                raw_response = client.explain(prompt)
                if raw_response and "LLM Explanation failed" in raw_response:
                    last_error = raw_response
                    raw_response = None
            except Exception as e:
                last_error = f"Legacy client also failed: {e}"

        if raw_response is None:
            logger.warning("AI chain recommendation failed on all providers: %s", last_error)
            return {
                "recommended_chain_ids": analysis_dict.get("recommendation", {}).get("recommended_chain_ids", []),
                "confidence": "low",
                "rationale": "The AI expert could not produce a structured recommendation (all LLM providers failed). Falling back to the fast heuristic result.",
                "warnings": [f"All LLM providers failed. Last error: {last_error or 'unknown'}. Configure GROQ_API_KEY (recommended) or another provider."],
                "source": "heuristic_fallback"
            }

        # Try to extract clean JSON (models often wrap it in ```json ... ```)
        parsed = DockingWorkspaceService._parse_ai_json_response(raw_response)

        if parsed and isinstance(parsed, dict) and parsed.get("recommended_chain_ids"):
            parsed["source"] = "ai_expert"
            parsed.setdefault("confidence", "medium")
            parsed.setdefault("warnings", [])
            return parsed

        # Graceful degradation — never break the user's workflow
        logger.warning("AI chain recommendation parse failed. Falling back to heuristic.")
        heuristic = analysis_dict.get("recommendation", {})
        debug_snippet = ""
        if raw_response:
            debug_snippet = "\n\nRaw model output (first 600 chars):\n" + str(raw_response)[:600]

        return {
            "recommended_chain_ids": heuristic.get("recommended_chain_ids", []),
            "confidence": "low",
            "rationale": "The AI expert could not produce a structured recommendation (model did not return valid JSON). Falling back to the fast heuristic result." + debug_snippet,
            "warnings": ["AI response could not be parsed as JSON — check prompt or model output format"],
            "source": "heuristic_fallback"
        }

    @staticmethod
    def _build_ai_chain_prompt(analysis: Dict[str, Any], ligand_smiles: Optional[str], target_name: Optional[str]) -> str:
        chains_json = json.dumps(analysis.get("chains", []), indent=2)

        # Preliminary size-based evidence only. We deliberately do NOT surface the
        # heuristic's recommended_chain_ids as "the recommendation" — doing so anchored
        # the LLM into simply repeating it. Instead we present chains ranked by size as
        # one weak signal the model is free to override.
        _ranked_chains = sorted(
            analysis.get("chains", []) or [],
            key=lambda c: (c.get("num_standard_aa") or c.get("num_residues") or 0),
            reverse=True,
        )
        size_ranked = ", ".join(
            f"{c.get('chain_id', '?')} ({c.get('num_standard_aa') or c.get('num_residues') or 0} residues)"
            for c in _ranked_chains
        ) or "unavailable"

        ligand_section = f"\nLigand the user intends to dock (SMILES): {ligand_smiles}" if ligand_smiles else ""
        target_section = f"\nUser-provided target / project notes: {target_name}" if target_name else ""

        return f"""You are a 25-year veteran medicinal chemist and structural biologist who has led more than 40 drug discovery programs from hit identification through clinical candidate nomination and IND filing. You have personally run and reviewed thousands of docking campaigns (Vina, Glide, Gold, MOE) across kinases, proteases, GPCRs, nuclear receptors, and protein-protein interfaces. You know every common PDB pitfall by heart.

A user has uploaded a protein structure for pre-docking analysis in a real drug discovery project. Here is the machine-generated structural summary:

{chains_json}

Fast heuristic observations (preliminary evidence only — this is NOT the recommendation):
Candidate chains ranked by size (largest first): {size_ranked}
This heuristic is based primarily on chain size and composition, not on binding-site biology, catalytic residues, ligand contacts, or biological assembly. Evaluate all available structural information independently. You may agree or disagree with this size ranking, and you should return the scientifically best chain even if it differs from the largest-chain ordering.
{ligand_section}{target_section}

Your task (think like the most experienced docking scientist on the team):
1. Recommend the single best chain ID (or small set of chains) that should be used for docking this ligand in a real medicinal chemistry program.
2. Write a concise, authoritative scientific rationale (4–7 sentences) that a real project team would find valuable. Explicitly reference:
   - Which chain contains the biologically relevant binding site (orthosteric, allosteric, or known cryptic site)
   - Any visible catalytic residues, conserved motifs, or key interaction points
   - Biological assembly considerations (the deposited ASU is often not the biological oligomer)
   - Why the other chains are less relevant (symmetry mates, crystallization artifacts, wrong domain, etc.)
   - Any specific red flags or opportunities for this target class or this PDB code
3. State your confidence (high / medium / low) with one short reason.
4. List any important warnings.

Return ONLY a single valid JSON object — nothing else. No markdown fences, no explanations, no text before or after the JSON. The response must start with {{ and end with }}.

{{
  "recommended_chain_ids": ["A"],
  "confidence": "high",
  "rationale": "Chain A contains the canonical ATP-binding site with the conserved DFG motif and HRD catalytic residues visible in the structure. Chain B is a symmetry mate that does not form the biological dimer interface used by this kinase family. The co-crystallized ligand sits in chain A...",
  "warnings": ["Chain B density is poor in the activation loop"]
}}

Think step-by-step as the 25-year expert before producing the JSON."""

    @staticmethod
    def _parse_ai_json_response(raw: str) -> Optional[Dict[str, Any]]:
        """Robustly extract JSON from LLM output (handles ```json fences and extra text)."""
        if not raw or not isinstance(raw, str):
            return None
        text = raw.strip()

        # Remove common markdown code fences
        if text.startswith("```"):
            # ```json ... ``` or ``` ... ```
            parts = text.split("```", 2)
            if len(parts) >= 2:
                text = parts[1]
            if text.lower().startswith("json"):
                text = text[4:].strip()

        # Try direct parse
        try:
            return json.loads(text)
        except Exception:
            pass

        # Try to find the first { ... } block
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                candidate = text[start:end+1]
                return json.loads(candidate)
        except Exception:
            pass

        return None

    # ── Existing method continues below ─────────────────────────────────

    @staticmethod
    def get_job_report(job_id: str) -> Dict[str, Any]:
        """Load the saved report.json + basic metadata for a completed docking job."""
        if not HAS_DOCKING:
            raise RuntimeError(_UNAVAILABLE_MSG)

        workspace = DockingWorkspaceService.get_workspace(job_id)
        report_path = os.path.join(workspace, "report.json")
        config_path = os.path.join(workspace, "config.json")

        if not os.path.exists(report_path):
            raise FileNotFoundError(f"No report found for docking job {job_id}")

        with open(report_path, encoding="utf-8") as f:
            report = json.load(f)

        # Attach some useful context
        report["job_id"] = job_id
        report["workspace"] = workspace

        if os.path.exists(config_path):
            try:
                with open(config_path, encoding="utf-8") as f:
                    report["grid_config"] = json.load(f)
            except Exception:
                pass

        # Also expose per-pose SDF paths if they exist (very useful for frontend)
        for pose in report.get("poses", []):
            sdf_path = os.path.join(workspace, f"pose_{pose['rank']}.sdf")
            if os.path.exists(sdf_path):
                pose["sdf_path"] = f"/outputs/docking_workspace/{job_id}/pose_{pose['rank']}.sdf"

        return report
