"""
core/pams/asset_service.py
=========================
ProteinAssetService — the single entry point where every protein becomes a
ProteinAsset, regardless of how it arrived.

Upload, RCSB fetch, AlphaFold, local file: all go through ``create_from_source``,
so uploaded and fetched proteins share exactly the same downstream workflow
(validation → analysis → persistence). This service is docking-free; structure
analysis is provided via the injected ``StructureAnalyzer`` port, whose concrete
implementation (backed by the existing analyze_receptor) lives outside PAMS core.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from core.pams.models import (
    ProteinAsset, Provenance, Origin, LifecycleStage, ArtifactKind, StructureMetadata,
    PreparationStatus, PreparationStep, StepStatus,
)
from core.pams.ports import AssetStore, StructureAnalyzer
from core.pams.sources.base import SourceRequest, RawStructure, SourceError
from core.pams.sources.registry import SourceRegistry

logger = logging.getLogger(__name__)

_PROVIDER_ORIGIN = {"upload": Origin.UPLOAD, "local": Origin.LOCAL}


def _origin_for(provider: str) -> Origin:
    return _PROVIDER_ORIGIN.get(provider, Origin.FETCH)


def _cif_to_pdb(cif_text: str) -> str:
    """Convert CIF/mmCIF to PDB so the viewer and docking pipeline always get PDB."""
    try:
        import gemmi
    except ImportError as exc:  # pragma: no cover - gemmi is a project dependency
        raise SourceError("CIF conversion requires gemmi, which is not installed.") from exc
    try:
        st = gemmi.read_structure_string(cif_text)
        return st.make_pdb_string()
    except Exception as exc:  # noqa: BLE001
        raise SourceError(f"Failed to convert CIF to PDB: {exc}") from exc


class ProteinAssetService:
    def __init__(self, registry: SourceRegistry, store: AssetStore,
                 analyzer: Optional[StructureAnalyzer] = None):
        self._registry = registry
        self._store = store
        self._analyzer = analyzer

    # -- creation (single converged path) ------------------------------------
    def create_from_source(self, request: SourceRequest,
                           requested_by: Optional[str] = None) -> ProteinAsset:
        source = self._registry.resolve(request)
        raw: RawStructure = source.fetch(request)

        pdb_text, primary_format, cif_text = self._normalize_structure(raw)

        asset = ProteinAsset(
            name=request.name or raw.name or (raw.provider_ref or "structure"),
            origin=_origin_for(raw.provider).value,
            provider=raw.provider if _origin_for(raw.provider) == Origin.FETCH else None,
            provider_ref=raw.provider_ref,
            primary_format=primary_format,
            metadata=raw.metadata or StructureMetadata(),
            provenance=Provenance(
                origin=_origin_for(raw.provider).value,
                provider=raw.provider,
                provider_ref=raw.provider_ref,
                source_url=raw.source_url,
                requested_by=requested_by,
                cached=raw.cached,
            ),
        )
        asset.advance_stage(LifecycleStage.DOWNLOADED)

        # Persist the canonical (PDB) source structure; keep CIF as an extra artifact.
        self._store.save(asset, pdb_text, ArtifactKind.SOURCE_STRUCTURE)
        if cif_text is not None:
            self._store.put_artifact(asset, ArtifactKind.SOURCE_STRUCTURE_CIF, cif_text,
                                     fmt="cif", produced_by=raw.provider)

        asset.advance_stage(LifecycleStage.VALIDATED)

        # Shared analysis — identical for uploaded and fetched proteins.
        if self._analyzer is not None:
            try:
                asset.metadata = self._analyzer.analyze(pdb_text, base=asset.metadata)
                asset.advance_stage(LifecycleStage.ANALYZED)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Structure analysis failed for asset %s: %s", asset.asset_id, exc)

        self._store._write_asset(asset)  # persist final metadata/stage
        return asset

    # -- convenience wrappers -------------------------------------------------
    def create_from_upload(self, pdb_text: str, name: Optional[str] = None,
                           requested_by: Optional[str] = None) -> ProteinAsset:
        return self.create_from_source(
            SourceRequest(source="upload", inline_text=pdb_text, name=name),
            requested_by=requested_by,
        )

    def fetch(self, identifier: str, source: Optional[str] = None, fmt: str = "pdb",
              requested_by: Optional[str] = None) -> ProteinAsset:
        return self.create_from_source(
            SourceRequest(source=source, identifier=identifier, fmt=fmt),
            requested_by=requested_by,
        )

    # -- lifecycle write-back (asset-native docking) -------------------------
    def attach_prepared_receptor(self, asset_id: str, pdbqt_text: str,
                                 options: Optional[dict] = None) -> Optional[ProteinAsset]:
        """Persist a prepared receptor PDBQT as an artifact on the asset and advance
        its lifecycle to DOCKING_READY. Returns None if the asset is unknown.

        This is how the docking preparation stage writes its result back into PAMS so
        the ProteinAsset accumulates its derived artifacts and becomes the source of
        truth across stages. PAMS core stays docking-free — the caller (docking route)
        hands us the already-produced PDBQT text."""
        asset = self._store.get(asset_id)
        if asset is None:
            return None
        self._store.put_artifact(
            asset, ArtifactKind.RECEPTOR_PDBQT, pdbqt_text, fmt="pdbqt", produced_by="preparation",
        )
        prep = asset.preparation
        prep.status = PreparationStatus.READY.value
        prep.docking_ready = True
        prep.prepared_artifact_kind = ArtifactKind.RECEPTOR_PDBQT
        if options is not None:
            prep.options = options
        prep.record_step(PreparationStep.PDBQT_GENERATED.value, StepStatus.DONE.value)
        asset.advance_stage(LifecycleStage.DOCKING_READY)
        self._store._write_asset(asset)
        return asset

    # -- reads ----------------------------------------------------------------
    def get(self, asset_id: str) -> Optional[ProteinAsset]:
        return self._store.get(asset_id)

    def get_structure_text(self, asset_id: str,
                           artifact_kind: str = ArtifactKind.SOURCE_STRUCTURE) -> Optional[str]:
        return self._store.get_artifact_text(asset_id, artifact_kind)

    def list(self, project_id: Optional[str] = None) -> List[ProteinAsset]:
        return self._store.list(project_id=project_id)

    def sources(self):
        return self._registry.list()

    # -- internal -------------------------------------------------------------
    @staticmethod
    def _normalize_structure(raw: RawStructure):
        """Return (pdb_text, primary_format, cif_text_or_None). Always yields PDB for
        the pipeline; if the source gave CIF, convert and keep the CIF alongside."""
        if raw.fmt == "cif":
            return _cif_to_pdb(raw.text), "pdb", raw.text
        return raw.text, "pdb", None


__all__ = ["ProteinAssetService"]
