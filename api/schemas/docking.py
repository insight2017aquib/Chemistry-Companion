"""
api/schemas/docking.py
======================
Pydantic schemas for the Advanced Docking workspace (Phase 1+).

Includes models for:
- Pre-docking protein analysis (chain identification + recommendation)
- Future docking-related request/response shapes
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# ── Pre-docking Protein Analysis (Phase 1) ────────────────────────────────

class ChainInfoSchema(BaseModel):
    """Detailed information about one chain (returned by /protein_analyze)."""
    chain_id: str
    num_residues: int = 0
    num_standard_aa: int = 0
    first_resnum: Optional[int] = None
    last_resnum: Optional[int] = None
    num_hetero: int = 0
    hetero_names: List[str] = Field(default_factory=list)
    num_waters: int = 0
    is_likely_protein: bool = False
    sample_residues: List[str] = Field(default_factory=list)


class ProteinAnalysisResult(BaseModel):
    """Full response from pre-docking protein inspection."""
    chains: List[ChainInfoSchema]
    total_chains: int
    total_residues: int
    total_waters: int
    total_hetero_groups: int
    hetero_ligand_names: List[str]
    num_models: int = 1
    format_detected: str = "pdb"
    recommendation: Dict[str, Any] = Field(default_factory=dict)


class ProteinAnalyzeRequest(BaseModel):
    """Request body for POST /api/docking/protein_analyze.

    Accepts either raw ``pdb_text`` (backward compatible) or an ``asset_id`` that the
    server resolves to structure text from PAMS (asset-native docking)."""
    pdb_text: str = ""
    asset_id: Optional[str] = None
    # Future: could add options like "ignore_waters", "focus_near_hets", etc.


# ── New Rich Receptor Analysis (Phase 1+) ────────────────────────────────

class ReceptorAnalysisResult(BaseModel):
    """
    Richer response from /receptor/analyze.
    Contains everything from ProteinAnalysisResult plus new scientific fields.
    """
    chains: List[ChainInfoSchema]
    total_chains: int
    total_residues: int
    total_waters: int
    total_hetero_groups: int
    num_models: int = 1
    format_detected: str = "pdb"
    recommendation: Dict[str, Any] = Field(default_factory=dict)

    # New rich fields
    ligands: List[Dict[str, Any]] = Field(default_factory=list)
    cofactors: List[Dict[str, Any]] = Field(default_factory=list)
    metals: List[Dict[str, Any]] = Field(default_factory=list)
    resolution: Optional[float] = None
    experimental_method: Optional[str] = None
    has_biological_assembly: bool = False
    missing_residues: List[Dict[str, Any]] = Field(default_factory=list)
    quality_score: float = 0.0
    quality_label: str = "Unknown"


class ProteinChainsResult(BaseModel):
    chains: List[Dict[str, Any]]
    total_chains: int
    recommendation: Dict[str, Any] = Field(default_factory=dict)


class ProteinWatersResult(BaseModel):
    waters: List[Dict[str, Any]]
    summary: Dict[str, Any]
    total: int


class ProteinCofactorsResult(BaseModel):
    cofactors: List[Dict[str, Any]]
    total: int


class ProteinMetalsResult(BaseModel):
    metals: List[Dict[str, Any]]
    total: int


class ProteinQualityResult(BaseModel):
    score: float
    label: str
    breakdown: Dict[str, float]
    notes: List[str]
