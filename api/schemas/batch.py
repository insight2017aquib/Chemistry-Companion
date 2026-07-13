"""
api/schemas/batch.py
====================
Pydantic schemas for batch processing requests and responses.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class BatchRequest(BaseModel):
    """Request for batch molecule analysis."""

    molecules: List[Dict[str, str]] = Field(
        ...,
        description="List of molecule inputs (each with smiles/inchi/iupac/name)"
    )
    include_spectra: bool = Field(True, description="Include spectral predictions")
    save_images: bool = Field(False, description="Generate 2D structure images")
    export_formats: List[str] = Field(
        default_factory=lambda: ["csv"],
        description="Export formats to generate"
    )
    output_dir: Optional[str] = Field(None, description="Output directory path")

    class Config:
        json_schema_extra = {
            "example": {
                "molecules": [
                    {"smiles": "c1ccccc1", "name": "Benzene"},
                    {"smiles": "CCO", "name": "Ethanol"},
                    {"smiles": "CC(=O)O", "name": "Acetic Acid"}
                ],
                "include_spectra": True,
                "save_images": True,
                "export_formats": ["csv", "json"]
            }
        }


class BatchMoleculeResult(BaseModel):
    """Result for a single molecule in batch processing."""

    input: Dict[str, str]
    success: bool
    molecule: Optional[Dict] = None
    descriptors: Optional[Dict] = None
    functional_groups: Optional[Dict[str, int]] = None
    ir_prediction: Optional[Dict] = None
    proton_nmr_prediction: Optional[Dict] = None
    carbon_nmr_prediction: Optional[Dict] = None
    visualization_path: Optional[str] = None
    error: Optional[str] = None


class BatchResponse(BaseModel):
    """Response for batch processing."""

    total_molecules: int
    successful_analyses: int
    failed_analyses: int
    results: List[BatchMoleculeResult] = Field(default_factory=list)
    export_paths: Dict[str, str] = Field(default_factory=dict)
    summary: Dict[str, int] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "total_molecules": 3,
                "successful_analyses": 3,
                "failed_analyses": 0,
                "results": [
                    {
                        "input": {"smiles": "c1ccccc1", "name": "Benzene"},
                        "success": True,
                        "molecule": {"formula": "C6H6"},
                        "descriptors": {"molecular_weight": 78.11}
                    }
                ],
                "export_paths": {
                    "csv": "/output/batch_results.csv",
                    "json": "/output/batch_results.json"
                }
            }
        }


class BatchProgress(BaseModel):
    """Progress update for batch processing."""

    total: int
    completed: int
    current_molecule: Optional[str] = None
    status: str = "processing"
    estimated_time_remaining: Optional[float] = None