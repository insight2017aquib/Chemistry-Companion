"""
services/screening_service.py
=============================
Core logic for Virtual Screening batch processing.
Uses asyncio semaphores to manage concurrency for AutoDock Vina jobs.
Reuses standard docking_workspace prepare steps to prevent technical debt.
"""

import os
import uuid
import json
import asyncio
import logging
import csv
import io
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session
from database.models import ScreeningWorkspace, ScreeningHit, get_db

from services.clustering_service import get_murcko_scaffold

logger = logging.getLogger(__name__)

# Directory to save heavy batch results
SCREENING_DATA_DIR = os.path.join(os.getcwd(), "outputs", "screening_workspace")
os.makedirs(SCREENING_DATA_DIR, exist_ok=True)

class ScreeningService:
    def __init__(self, db: Session):
        self.db = db

    def _parse_library(self, file_content: str, filename: str) -> List[Dict[str, str]]:
        """
        Robustly parses a CSV file into a list of dictionaries with 'smiles' and 'name'.
        Supports quoted fields, UTF-8 BOM, various column namings, and ignores duplicates.
        """
        # 1. Strip UTF-8 BOM
        if file_content.startswith('\ufeff'):
            file_content = file_content[1:]
            
        file_content = file_content.strip()
        if not file_content:
            logger.warning("Empty CSV file provided.")
            return []
            
        f = io.StringIO(file_content)
        reader = csv.reader(f)
        
        try:
            first_row = next(reader)
        except StopIteration:
            logger.warning("Empty CSV file provided.")
            return []
            
        # 2. Detect Columns (case-insensitive)
        first_row_lower = [col.strip().lower() for col in first_row]
        
        smiles_col_names = ["smiles"]
        name_col_names = ["compound_name", "name", "ligand_name", "ligand", "ligand_id", "id"]
        
        smiles_idx = None
        name_idx = None
        is_header = False
        
        for possible_name in smiles_col_names:
            if possible_name in first_row_lower:
                smiles_idx = first_row_lower.index(possible_name)
                is_header = True
                break
                
        for possible_name in name_col_names:
            if possible_name in first_row_lower:
                name_idx = first_row_lower.index(possible_name)
                is_header = True
                break
                
        # 3. Header vs Headerless Handling
        if not is_header:
            rows_to_process = [first_row]
            smiles_idx = 0
            name_idx = 1 if len(first_row) > 1 else None
        else:
            rows_to_process = []
            if smiles_idx is None:
                smiles_idx = 0
                
        def row_generator():
            yield from rows_to_process
            yield from reader
            
        ligands = []
        seen_smiles = set()
        ligand_counter = 1
        
        skipped_empty = 0
        skipped_invalid = 0
        skipped_duplicate = 0
        
        # 4. Process Rows
        for row in row_generator():
            # Filter empty rows (e.g. `[]` or `['', '']`)
            if not row or all(not col.strip() for col in row):
                skipped_empty += 1
                continue
                
            if smiles_idx >= len(row):
                skipped_invalid += 1
                logger.warning(f"Skipped row due to missing SMILES column: {row}")
                continue
                
            smiles = row[smiles_idx].strip()
            
            # Validation: missing, empty, or whitespace-only SMILES
            if not smiles:
                skipped_invalid += 1
                logger.warning(f"Skipped row due to empty SMILES: {row}")
                continue
                
            # Duplicate handling
            if smiles in seen_smiles:
                skipped_duplicate += 1
                logger.warning(f"Skipped duplicate SMILES: {smiles}")
                continue
                
            seen_smiles.add(smiles)
            
            # Name Handling
            name = None
            if name_idx is not None and name_idx < len(row):
                name = row[name_idx].strip()
                
            if not name:
                name = f"Ligand_{ligand_counter}"
                ligand_counter += 1
                
            ligands.append({"smiles": smiles, "name": name})
            
        logger.info(f"Imported {len(ligands)} ligands. Skipped {skipped_invalid} invalid SMILES. Skipped {skipped_empty} empty row(s). Skipped {skipped_duplicate} duplicate(s).")
        
        return ligands

    def create_job(self, workspace_id: str, grid_config: Dict, file_content: str, filename: str, exhaustiveness: int = 8) -> str:
        """Initialize a new screening job in the database."""
        ligands = self._parse_library(file_content, filename)
        if not ligands:
            raise ValueError("No valid ligands found in library file.")

        job_id = f"scr_{uuid.uuid4().hex[:12]}"
        
        job = ScreeningWorkspace(
            id=job_id,
            workspace_id=workspace_id,
            name=f"Screening: {filename}",
            library_name=filename,
            total_ligands=len(ligands),
            grid_config=grid_config,
            exhaustiveness=exhaustiveness,
            status="queued",
            started_at=datetime.utcnow()
        )
        
        self.db.add(job)
        
        # Add hits to DB
        for lig in ligands:
            hit = ScreeningHit(
                id=f"hit_{uuid.uuid4().hex[:12]}",
                screening_id=job_id,
                ligand_name=lig.get("name"),
                smiles=lig.get("smiles"),
                scaffold_smiles=get_murcko_scaffold(lig.get("smiles")),
                status="queued"
            )
            self.db.add(hit)
            
        self.db.commit()
        return job_id

    @staticmethod
    def _parse_vina_affinity(pdbqt_out: str, log_text: str = "") -> Optional[float]:
        """Extract best affinity (kcal/mol) from Vina output PDBQT or log."""
        import re

        for text in (pdbqt_out or "", log_text or ""):
            m = re.search(r"REMARK VINA RESULT:\s+(-?\d+\.?\d*)", text)
            if m:
                return float(m.group(1))
            m = re.search(r"Affinity:\s*(-?\d+\.?\d*)\s*\(kcal/mol\)", text)
            if m:
                return float(m.group(1))
            m = re.search(
                r"Estimated Free Energy of Binding\s*[:=]\s*(-?\d+\.?\d*)", text
            )
            if m:
                return float(m.group(1))
        return None

    async def _process_ligand(self, hit: ScreeningHit, receptor_pdbqt: str, grid: Dict, exhaustiveness: int):
        """Prepare ligand (real RDKit/OpenBabel) and dock with AutoDock Vina."""
        loop = asyncio.get_event_loop()
        try:
            from core.docking_preparation import prepare_docking_structure
            from docking_workflow.vina_runner import run_vina

            smiles = (hit.smiles or "").strip()
            if not smiles:
                raise ValueError("Hit has empty SMILES")

            def _prepare() -> str:
                return prepare_docking_structure(
                    smiles,
                    output_format="pdbqt",
                    optimization_method="mmff94",
                    ph=7.4,
                )

            ligand_pdbqt = await loop.run_in_executor(None, _prepare)
            ligand_pdbqt_path = os.path.join(SCREENING_DATA_DIR, f"{hit.id}_ligand.pdbqt")
            with open(ligand_pdbqt_path, "w", encoding="utf-8") as f:
                f.write(ligand_pdbqt)

            # Receptor may be path or PDBQT text
            if receptor_pdbqt and os.path.isfile(receptor_pdbqt):
                with open(receptor_pdbqt, "r", encoding="utf-8") as f:
                    protein_content = f.read()
            else:
                protein_content = receptor_pdbqt or ""
            if not protein_content.strip():
                raise ValueError("Receptor PDBQT content is empty")

            def _dock():
                return run_vina(
                    protein_content,
                    ligand_pdbqt,
                    float(grid["center_x"]),
                    float(grid["center_y"]),
                    float(grid["center_z"]),
                    float(grid["size_x"]),
                    float(grid["size_y"]),
                    float(grid["size_z"]),
                    exhaustiveness=int(exhaustiveness or 8),
                    num_modes=1,
                    timeout=300,
                )

            result = await loop.run_in_executor(None, _dock)
            out_pdbqt_path = os.path.join(SCREENING_DATA_DIR, f"{hit.id}_out.pdbqt")
            log_path = os.path.join(SCREENING_DATA_DIR, f"{hit.id}_vina.log")
            with open(out_pdbqt_path, "w", encoding="utf-8") as f:
                f.write(result.pdbqt_output or "")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(result.log_text or "")

            affinity = self._parse_vina_affinity(result.pdbqt_output or "", result.log_text or "")
            if affinity is None:
                raise RuntimeError("Vina completed but no affinity could be parsed from output")

            hit.status = "completed"
            hit.best_affinity = str(affinity)
            hit.affinity_value = int(round(affinity * 100))
            hit.pose_path = out_pdbqt_path

        except Exception as e:
            hit.status = "failed"
            hit.error_message = str(e)
            logger.error(f"Failed hit {hit.id}: {e}")

    async def run_screening_job(self, job_id: str, receptor_pdbqt: str):
        """Main async task that coordinates the semaphore pool."""
        job = self.db.query(ScreeningWorkspace).filter_by(id=job_id).first()
        if not job:
            return
            
        job.status = "running"
        self.db.commit()
        
        hits = self.db.query(ScreeningHit).filter_by(screening_id=job_id).all()
        
        # Bounded concurrency to prevent CPU starvation
        # Vina is multi-threaded, so limit concurrent Vina runs to CPU_COUNT // EXHAUSTIVENESS
        import multiprocessing
        max_workers = max(1, multiprocessing.cpu_count() // 2)
        semaphore = asyncio.Semaphore(max_workers)
        
        async def bounded_worker(hit):
            async with semaphore:
                # Update DB state for UI
                hit.status = "running"
                self.db.commit()
                
                await self._process_ligand(hit, receptor_pdbqt, job.grid_config, job.exhaustiveness)
                
                # Update counters
                job.completed_ligands += 1
                job.progress = {"percent": int(job.completed_ligands / job.total_ligands * 100)}
                self.db.commit()
                
        tasks = [asyncio.create_task(bounded_worker(h)) for h in hits]
        await asyncio.gather(*tasks)
        
        # Calculate metrics
        completed = [h for h in hits if h.status == "completed"]
        if completed:
            avg = sum(float(h.best_affinity) for h in completed) / len(completed)
            best = min(float(h.best_affinity) for h in completed)
            job.metrics = {"avg_affinity": round(avg, 2), "best_affinity": best}
            
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        self.db.commit()
