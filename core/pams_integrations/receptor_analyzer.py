"""
core/pams_integrations/receptor_analyzer.py
==========================================
StructureAnalyzer implementation backed by the EXISTING analyze_receptor().

This is the single bridge from PAMS to structure analysis. It reuses
docking_workflow.analyze_receptor (no analysis logic is duplicated) and maps its
ReceptorReport onto the normalized PAMS StructureMetadata. Because this lives
outside core/pams, the PAMS core remains docking-independent.
"""

from __future__ import annotations

import logging
from typing import Optional

from core.pams.models import (
    StructureMetadata, ChainSummary, LigandSummary,
)
from core.pams.ports import StructureAnalyzer

logger = logging.getLogger(__name__)


class ReceptorReportAnalyzer(StructureAnalyzer):
    """Adapts docking_workflow.analyze_receptor to the PAMS StructureAnalyzer port."""

    def analyze(self, structure_text: str,
                base: Optional[StructureMetadata] = None) -> StructureMetadata:
        from docking_workflow.protein_analysis import analyze_receptor

        report = analyze_receptor(structure_text)
        md = base or StructureMetadata()

        # Analysis fills structural detail; source metadata (title/resolution) is
        # preserved unless the analysis has a better value.
        md.chains = [
            ChainSummary(
                chain_id=c.chain_id,
                num_residues=c.num_residues,
                num_standard_aa=c.num_standard_aa,
                is_protein=c.is_likely_protein,
                first_resnum=c.first_resnum,
                last_resnum=c.last_resnum,
            )
            for c in report.chains
        ]
        md.ligands = [
            LigandSummary(
                resname=l.resname,
                chain_id=l.chain_id,
                resnum=l.resnum,
                num_atoms=l.num_atoms,
                centroid=l.centroid,
                role="cocrystal",
            )
            for l in report.ligands
        ]
        if md.resolution is None and getattr(report, "resolution", None) is not None:
            md.resolution = report.resolution
        if md.method is None and getattr(report, "experimental_method", None):
            md.method = report.experimental_method
        return md


def build_service(root: str, http=None):
    """Compose a fully-wired PAMS service (with shared analysis) for the app layer."""
    from core.pams import build_core_service
    return build_core_service(root, http=http, analyzer=ReceptorReportAnalyzer())


__all__ = ["ReceptorReportAnalyzer", "build_service"]
