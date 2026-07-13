"""
core/pams/ports.py
=================
Ports (interfaces) the PAMS core depends on but does not implement itself.

Keeping these as Protocols is what keeps the core decoupled and testable:
  * ``AssetStore`` — persistence (filesystem now, SQL later) without touching callers.
  * ``StructureAnalyzer`` — structure analysis WITHOUT importing docking. The concrete
    adapter that reuses docking_workflow.analyze_receptor lives OUTSIDE this package
    (core/pams_integrations/), so the PAMS core never imports docking. This preserves
    "fetch pipeline independent of docking" while still sharing one analysis impl.
"""

from __future__ import annotations

from typing import List, Optional, Protocol

from core.pams.models import ProteinAsset, StructureMetadata


class AssetStore(Protocol):
    def save(self, asset: ProteinAsset, structure_text: str, artifact_kind: str) -> None: ...
    def get(self, asset_id: str) -> Optional[ProteinAsset]: ...
    def get_artifact_text(self, asset_id: str, artifact_kind: str) -> Optional[str]: ...
    def put_artifact(self, asset: ProteinAsset, kind: str, text: str,
                     fmt: str = "", produced_by: str = "") -> None: ...
    def list(self, project_id: Optional[str] = None) -> List[ProteinAsset]: ...
    def delete(self, asset_id: str) -> bool: ...


class StructureAnalyzer(Protocol):
    """Analyzes raw structure text into normalized metadata (chains, ligands, ...).

    Implemented outside PAMS core by an adapter over the existing analyze_receptor,
    so analysis logic is never duplicated."""
    def analyze(self, structure_text: str, base: Optional[StructureMetadata] = None) -> StructureMetadata: ...


__all__ = ["AssetStore", "StructureAnalyzer"]
