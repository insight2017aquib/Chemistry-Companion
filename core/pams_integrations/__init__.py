"""
core/pams_integrations — adapters that bridge PAMS to the rest of Chemistry
Companion (docking analysis, and later preparation/docking result write-back).

This package is ALLOWED to import docking_workflow. The PAMS core (core/pams) is
NOT — an import-lint test enforces that boundary, preventing PAMS from becoming
coupled to the docking pipeline.
"""

from core.pams_integrations.receptor_analyzer import ReceptorReportAnalyzer, build_service

__all__ = ["ReceptorReportAnalyzer", "build_service"]
