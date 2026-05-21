"""
api/routes/structure.py
=======================
2D structure image endpoints (PNG / SVG).
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from core.molecule_utils import load_molecule
from core.visualization_utils import mol_to_png_bytes, mol_to_svg_string

logger = logging.getLogger(__name__)
router = APIRouter()


def _load_mol(
    smiles: Optional[str] = None,
    inchi: Optional[str] = None,
    iupac: Optional[str] = None,
):
    record = load_molecule(smiles=smiles, inchi=inchi, iupac_name=iupac or None)
    if record.rdkit_mol is None:
        raise HTTPException(status_code=400, detail="Invalid molecule input")
    return record.rdkit_mol, record.smiles


@router.get("/structure.png")
async def structure_png(
    smiles: Optional[str] = Query(None),
    inchi: Optional[str] = Query(None),
    iupac: Optional[str] = Query(None),
    width: int = Query(400, ge=100, le=1200),
    height: int = Query(400, ge=100, le=1200),
    atom_numbering: bool = Query(False),
    highlight_aromatic: bool = Query(False),
):
    """Return 2D structure as PNG."""
    try:
        mol, _ = _load_mol(smiles=smiles, inchi=inchi, iupac=iupac)
        png = mol_to_png_bytes(
            mol,
            size=(width, height),
            atom_numbering=atom_numbering,
            highlight_aromatic_rings=highlight_aromatic,
        )
        return Response(content=png, media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Structure PNG failed: %s", e)
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/structure.svg")
async def structure_svg(
    smiles: Optional[str] = Query(None),
    inchi: Optional[str] = Query(None),
    iupac: Optional[str] = Query(None),
    width: int = Query(400, ge=100, le=1200),
    height: int = Query(400, ge=100, le=1200),
    atom_numbering: bool = Query(False),
    highlight_aromatic: bool = Query(False),
):
    """Return 2D structure as SVG."""
    try:
        mol, _ = _load_mol(smiles=smiles, inchi=inchi, iupac=iupac)
        svg = mol_to_svg_string(
            mol,
            size=(width, height),
            atom_numbering=atom_numbering,
            highlight_aromatic_rings=highlight_aromatic,
        )
        return Response(content=svg, media_type="image/svg+xml")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Structure SVG failed: %s", e)
        raise HTTPException(status_code=400, detail=str(e)) from e
