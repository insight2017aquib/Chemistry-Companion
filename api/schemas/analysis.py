"""
api/schemas/analysis.py
=======================
Pydantic schemas for molecule analysis requests and responses.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MoleculeInput(BaseModel):
    """Input for molecule analysis."""

    smiles: Optional[str] = Field(None, description="SMILES string")
    inchi: Optional[str] = Field(None, description="InChI string")
    iupac: Optional[str] = Field(None, description="IUPAC name")
    name: Optional[str] = Field(None, description="Molecule name")

    class Config:
        schema_extra = {
            "example": {
                "smiles": "c1ccccc1",
                "name": "Benzene"
            }
        }


class AnalysisRequest(BaseModel):
    """Request for complete molecule analysis."""

    molecule: MoleculeInput = Field(..., description="Molecule input data")
    include_spectra: bool = Field(True, description="Include spectral predictions")
    save_image: bool = Field(False, description="Generate 2D structure image")
    export_formats: List[str] = Field(default_factory=list, description="Export formats")

    class Config:
        schema_extra = {
            "example": {
                "molecule": {
                    "smiles": "CC(=O)O",
                    "name": "Acetic Acid"
                },
                "include_spectra": True,
                "save_image": True,
                "export_formats": ["csv", "json"]
            }
        }


class DescriptorResponse(BaseModel):
    """Molecular descriptor data."""

    molecular_weight: Optional[float]
    exact_mass: Optional[float]
    formula: Optional[str]
    logp: Optional[float]
    tpsa: Optional[float]
    hbd: Optional[int]
    hba: Optional[int]
    rotatable_bonds: Optional[int]
    ring_count: Optional[int]
    heavy_atom_count: Optional[int]
    formal_charge: Optional[int]
    fraction_csp3: Optional[float]
    functional_groups: Dict[str, int] = Field(default_factory=dict)
    bertz_ct: Optional[float]


class FunctionalGroupResponse(BaseModel):
    """Functional group analysis data."""

    keys: List[str] = Field(default_factory=list)
    names: List[str] = Field(default_factory=list)
    counts: Dict[str, int] = Field(default_factory=dict)
    categories: List[str] = Field(default_factory=list)
    summary_text: str = ""


class IRBandResponse(BaseModel):
    """IR band data."""

    fg_key: str
    fg_name: str
    label: str
    low_cm: int
    high_cm: int
    mid_cm: int
    intensity: str
    description: str
    is_heuristic: bool = True


class IRPredictionResponse(BaseModel):
    """IR prediction data."""

    smiles: str
    bands: List[IRBandResponse] = Field(default_factory=list)
    fg_keys: List[str] = Field(default_factory=list)
    fg_names: List[str] = Field(default_factory=list)
    n_bands: int = 0
    warnings: List[str] = Field(default_factory=list)
    is_heuristic: bool = True


class ProtonSignalResponse(BaseModel):
    """¹H NMR signal data."""

    label: str
    ppm_range: tuple[float, float]
    multiplicity: str
    integration: int
    description: str
    ppm_mid: float
    annotation: str
    environment_class: str
    confidence: str
    is_exchangeable: bool
    is_approximate: bool = True


class ProtonNMRResponse(BaseModel):
    """¹H NMR prediction data."""

    smiles: str
    signals: List[ProtonSignalResponse] = Field(default_factory=list)
    is_heuristic: bool = True
    warnings: List[str] = Field(default_factory=list)
    total_protons: int = 0
    n_signals: int = 0
    disclaimer: str = "HEURISTIC ONLY — approximate ppm ranges, not experimental values."


class CarbonEnvironmentResponse(BaseModel):
    """¹³C NMR carbon environment data."""

    label: str
    ppm_range: tuple[float, float]
    description: str
    rationale: str
    atom_indices: tuple[int, ...]
    carbon_count: int
    ppm_mid: float
    annotation: str
    environment_class: str
    confidence: str
    hybridization: str
    is_aromatic: bool
    is_heteroaromatic: bool
    heterocycle_family: Optional[str]
    hetero_position: Optional[str]
    ring_size: Optional[int]
    attached_elements: tuple[str, ...]
    n_attached_h: int
    is_quaternary: bool
    carbonyl_type: Optional[str]
    is_approximate: bool = True


class CarbonNMRResponse(BaseModel):
    """¹³C NMR prediction data."""

    smiles: str
    environments: List[CarbonEnvironmentResponse] = Field(default_factory=list)
    atom_environments: List[CarbonEnvironmentResponse] = Field(default_factory=list)
    is_heuristic: bool = True
    warnings: List[str] = Field(default_factory=list)
    total_carbons: int = 0
    n_signals: int = 0
    disclaimer: str = "HEURISTIC ONLY — approximate 13C ppm ranges, not experimental or quantum-accurate values."


class MoleculeResponse(BaseModel):
    """Molecule metadata."""

    smiles: str
    inchi: Optional[str]
    inchikey: Optional[str]
    name: Optional[str]
    formula: Optional[str]
    mol_weight: Optional[float]
    exact_mass: Optional[float]
    atom_counts: Dict[str, int] = Field(default_factory=dict)
    num_atoms: Optional[int]
    num_heavy_atoms: Optional[int]
    num_bonds: Optional[int]
    num_rings: Optional[int]
    is_aromatic: Optional[bool]


class AnalysisResponse(BaseModel):
    """Complete analysis response."""

    molecule: MoleculeResponse
    descriptors: DescriptorResponse
    descriptor_summary: str
    functional_groups: Dict[str, int] = Field(default_factory=dict)
    functional_group_report: FunctionalGroupResponse
    ir_prediction: Optional[IRPredictionResponse]
    proton_nmr_prediction: Optional[ProtonNMRResponse]
    carbon_nmr_prediction: Optional[CarbonNMRResponse]
    visualization_path: Optional[str]
    export_paths: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

    class Config:
        schema_extra = {
            "example": {
                "molecule": {
                    "smiles": "c1ccccc1",
                    "formula": "C6H6",
                    "name": "Benzene"
                },
                "descriptors": {
                    "molecular_weight": 78.11,
                    "logp": 1.6866,
                    "tpsa": 0.0
                },
                "functional_groups": {"aromatic_ring": 1},
                "ir_prediction": {
                    "bands": [
                        {
                            "label": "Ar C–H stretch",
                            "low_cm": 3000,
                            "high_cm": 3100,
                            "intensity": "medium"
                        }
                    ]
                }
            }
        }