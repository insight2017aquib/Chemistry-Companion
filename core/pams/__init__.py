"""
core/pams — Protein Asset Management System (core).

PURE core: no docking imports, no vendor-specific logic outside source adapters.
Structure analysis is provided by an injected StructureAnalyzer port; the concrete
adapter lives in core.pams_integrations so this package stays docking-independent.
"""

from __future__ import annotations

from typing import Optional

from core.pams.models import ProteinAsset, StructureMetadata, ArtifactKind, LifecycleStage
from core.pams.ports import AssetStore, StructureAnalyzer
from core.pams.store import FileSystemAssetStore
from core.pams.asset_service import ProteinAssetService
from core.pams.sources.registry import SourceRegistry
from core.pams.sources.base import SourceRequest
from core.pams.sources.rcsb import RCSBSource
from core.pams.sources.upload import UploadSource
from core.pams.sources.local import LocalFileSource
from core.pams.transport import HttpClient, RequestsHttpClient
from core.pams.cache import StructureCache, FileSystemStructureCache


def _remote_host_allowlist() -> set[str]:
    """Aggregate allowed hosts declared by the remote source adapters, so the
    transport SSRF guard is populated without hardcoding any vendor host here."""
    hosts: set[str] = set()
    hosts |= set(getattr(RCSBSource, "allowed_hosts", ()) or ())
    return hosts


def build_default_registry(
    http: Optional[HttpClient] = None,
    cache: Optional[StructureCache] = None,
) -> SourceRegistry:
    """Registry preloaded with the built-in sources. Add providers here (or call
    registry.register) — nothing else changes."""
    http = http or RequestsHttpClient(allowed_hosts=_remote_host_allowlist())
    registry = SourceRegistry()
    registry.register(RCSBSource(http, cache=cache))
    registry.register(UploadSource())
    registry.register(LocalFileSource())
    return registry


def build_core_service(
    root: str,
    http: Optional[HttpClient] = None,
    analyzer: Optional[StructureAnalyzer] = None,
    store: Optional[AssetStore] = None,
    cache: Optional[StructureCache] = None,
) -> ProteinAssetService:
    """Wire a docking-free PAMS service. Pass an analyzer (from pams_integrations)
    to enable shared structure analysis."""
    if cache is None:
        cache = FileSystemStructureCache(root.rstrip("/\\") + "_cache")
    registry = build_default_registry(http, cache=cache)
    store = store or FileSystemAssetStore(root)
    return ProteinAssetService(registry, store, analyzer=analyzer)


__all__ = [
    "ProteinAsset", "StructureMetadata", "ArtifactKind", "LifecycleStage",
    "ProteinAssetService", "SourceRegistry", "SourceRequest",
    "RCSBSource", "UploadSource", "LocalFileSource",
    "FileSystemAssetStore", "RequestsHttpClient", "FileSystemStructureCache",
    "build_default_registry", "build_core_service",
]
