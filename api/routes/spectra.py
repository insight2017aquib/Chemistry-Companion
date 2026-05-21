"""
api/routes/spectra.py
=====================
FastAPI routes for spectral predictions.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException

from ..schemas.analysis import MoleculeInput
from ..schemas.spectra import (
    IRPredictionResponse,
    ProtonNMRResponse,
    CarbonNMRResponse,
)
from services import SpectraService
from core.molecule_utils import mol_from_smiles

logger = logging.getLogger(__name__)

router = APIRouter()
spectra_service = SpectraService()


@router.post("/ir", response_model=IRPredictionResponse)
async def predict_ir(request: MoleculeInput) -> IRPredictionResponse:
    """
    Predict IR spectrum for a molecule.
    """
    try:
        # Convert input to molecule
        mol = mol_from_smiles(request.smiles)
        if mol is None:
            if request.inchi:
                mol = mol_from_smiles(request.inchi)  # Try InChI as SMILES fallback
            if mol is None:
                raise HTTPException(status_code=400, detail="Invalid molecule input")

        # Predict IR
        prediction = spectra_service.predict_ir(mol)

        if prediction is None:
            raise HTTPException(status_code=500, detail="IR prediction failed")

        return IRPredictionResponse(
            molecule=request,
            prediction=prediction,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"IR prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"IR prediction failed: {str(e)}")


@router.post("/hnmr", response_model=ProtonNMRResponse)
async def predict_proton_nmr(request: MoleculeInput) -> ProtonNMRResponse:
    """
    Predict ¹H NMR spectrum for a molecule.
    """
    try:
        # Convert input to molecule
        mol = mol_from_smiles(request.smiles)
        if mol is None:
            if request.inchi:
                mol = mol_from_smiles(request.inchi)
            if mol is None:
                raise HTTPException(status_code=400, detail="Invalid molecule input")

        # Predict ¹H NMR
        prediction = spectra_service.predict_proton_nmr(mol)

        if prediction is None:
            raise HTTPException(status_code=500, detail="¹H NMR prediction failed")

        return ProtonNMRResponse(
            molecule=request,
            prediction=prediction,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"¹H NMR prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"¹H NMR prediction failed: {str(e)}")


@router.post("/cnmr", response_model=CarbonNMRResponse)
async def predict_carbon_nmr(request: MoleculeInput) -> CarbonNMRResponse:
    """
    Predict ¹³C NMR spectrum for a molecule.
    """
    try:
        # Convert input to molecule
        mol = mol_from_smiles(request.smiles)
        if mol is None:
            if request.inchi:
                mol = mol_from_smiles(request.inchi)
            if mol is None:
                raise HTTPException(status_code=400, detail="Invalid molecule input")

        # Predict ¹³C NMR
        prediction = spectra_service.predict_carbon_nmr(mol)

        if prediction is None:
            raise HTTPException(status_code=500, detail="¹³C NMR prediction failed")

        return CarbonNMRResponse(
            molecule=request,
            prediction=prediction,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"¹³C NMR prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"¹³C NMR prediction failed: {str(e)}")