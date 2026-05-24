"""
api/routes/docking.py
=====================
Docking API endpoints.
"""

import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Form, HTTPException, Request

from core.docking_preparation import prepare_docking_structure

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/docking/generate")
async def generate_docking(
    request: Request,
    input_text: str = Form(...),
    ph: float = Form(7.4),
    forcefield: str = Form("mmff94")
) -> dict[str, Any]:
    """Generate a PDBQT file for docking and return status + download URL."""
    try:
        # Note: input_text contains the SMILES
        pdbqt_content = prepare_docking_structure(
            smiles=input_text,
            output_format="pdbqt",
            optimization_method=forcefield
        )
        
        # Save to outputs/docking
        job_id = str(uuid.uuid4())
        filename = f"{job_id}.pdbqt"
        output_dir = Path(__file__).parent.parent.parent / "outputs" / "docking"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / filename
        output_path.write_text(pdbqt_content, encoding="utf-8")
        
        return {
            "success": True,
            "job_id": job_id,
            "pdbqt": pdbqt_content,
            "pdbqt_content": pdbqt_content,
            "download_url": f"/outputs/docking/{filename}",
            "status": "completed"
        }
    except Exception as exc:
        logger.error("Docking generation failed: %s", exc, exc_info=True)
        return {
            "success": False,
            "error": str(exc),
            "status": "failed"
        }
