"""
api/schemas/spectra.py
======================
Pydantic schemas for spectral prediction requests and responses.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class IRBandSchema(BaseModel):
    """IR band data."""

    fg_key: str = Field(..., description="Functional group key")
    fg_name: str = Field(..., description="Functional group name")
    label: str = Field(..., description="Band label")
    low_cm: int = Field(..., description="Lower wavenumber (cm⁻¹)")
    high_cm: int = Field(..., description="Upper wavenumber (cm⁻¹)")
    mid_cm: int = Field(..., description="Mid wavenumber (cm⁻¹)")
    intensity: str = Field(..., description="Intensity (strong/medium/weak/broad)")
    description: str = Field(..., description="Band description")
    is_heuristic: bool = Field(True, description="Is heuristic prediction")


class IRPredictionResponse(BaseModel):
    """IR spectrum prediction response."""

    molecule: Any = Field(..., description="Molecule input data")
    smiles: Optional[str] = Field(None, description="SMILES string")
    bands: List[IRBandSchema] = Field(default_factory=list, description="Predicted IR bands")
    fg_keys: List[str] = Field(default_factory=list, description="Functional group keys")
    fg_names: List[str] = Field(default_factory=list, description="Functional group names")
    n_bands: int = Field(0, description="Number of bands")
    warnings: List[str] = Field(default_factory=list, description="Prediction warnings")
    is_heuristic: bool = Field(True, description="Is heuristic prediction")

    class Config:
        schema_extra = {
            "example": {
                "molecule": {"smiles": "c1ccccc1"},
                "smiles": "c1ccccc1",
                "bands": [],
                "fg_keys": [],
                "fg_names": [],
                "n_bands": 0,
                "warnings": [],
                "is_heuristic": True
            }
        }


class NMRPeakSchema(BaseModel):
    """NMR peak data."""

    shift: float = Field(..., description="Chemical shift (ppm)")
    height: Optional[float] = Field(None, description="Peak height")
    integration: Optional[float] = Field(None, description="Peak integration")
    multiplicity: Optional[str] = Field(None, description="Multiplicity")


class ProtonNMRResponse(BaseModel):
    """¹H NMR spectrum prediction response."""

    molecule: Any = Field(..., description="Molecule input data")
    smiles: Optional[str] = Field(None, description="SMILES string")
    peaks: List[NMRPeakSchema] = Field(default_factory=list, description="Predicted peaks")
    summary: Optional[str] = Field(None, description="Prediction summary")
    warnings: List[str] = Field(default_factory=list, description="Prediction warnings")

    class Config:
        schema_extra = {
            "example": {
                "molecule": {"smiles": "c1ccccc1"},
                "smiles": "c1ccccc1",
                "peaks": [],
                "summary": None,
                "warnings": []
            }
        }


class CarbonNMRResponse(BaseModel):
    """¹³C NMR spectrum prediction response."""

    molecule: Any = Field(..., description="Molecule input data")
    smiles: Optional[str] = Field(None, description="SMILES string")
    peaks: List[NMRPeakSchema] = Field(default_factory=list, description="Predicted peaks")
    summary: Optional[str] = Field(None, description="Prediction summary")
    warnings: List[str] = Field(default_factory=list, description="Prediction warnings")

    class Config:
        schema_extra = {
            "example": {
                "molecule": {"smiles": "c1ccccc1"},
                "smiles": "c1ccccc1",
                "peaks": [],
                "summary": None,
                "warnings": []
            }
        }
