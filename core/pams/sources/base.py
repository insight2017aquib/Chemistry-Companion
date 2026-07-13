"""
core/pams/sources/base.py
=========================
Structure source plugin contract.

Every way a protein enters the system — remote fetch (RCSB, AlphaFold, PDBe,
PDB-REDO) or local ingestion (upload, file on disk) — is a ``StructureSource``.
Adding a provider means adding one adapter that implements this Protocol and
registering it; **no code outside the adapter changes**.

Nothing here knows about any specific vendor. RCSB/AlphaFold/etc. specifics live
only in their own adapter modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol

from core.pams.models import StructureMetadata


class SourceError(RuntimeError):
    """Raised by a source adapter for validation/not-found/parse failures."""


class SourceNotFound(SourceError):
    """The requested identifier does not exist at this source."""


@dataclass
class SourceRequest:
    """A source-agnostic request to create a structure.

    Remote sources use ``identifier`` (+ ``fmt``); ingestion sources use
    ``inline_text`` (upload) or ``path`` (local file). ``source`` selects the
    adapter; when omitted the registry auto-detects.
    """
    source: Optional[str] = None
    identifier: Optional[str] = None
    inline_text: Optional[str] = None
    path: Optional[str] = None
    fmt: str = "pdb"
    name: Optional[str] = None


@dataclass
class RawStructure:
    """What a source adapter returns: the structure bytes plus provenance and any
    provider-native metadata (normalized later by the service/analyzer)."""
    text: str
    fmt: str
    provider: str
    provider_ref: Optional[str] = None
    source_url: Optional[str] = None
    name: Optional[str] = None
    metadata: Optional[StructureMetadata] = None
    raw_metadata: Dict[str, object] = field(default_factory=dict)
    cached: bool = False


@dataclass
class SourceCapabilities:
    formats: List[str] = field(default_factory=lambda: ["pdb"])
    has_metadata: bool = False
    id_kinds: List[str] = field(default_factory=list)   # e.g. ["pdb_id"], ["uniprot"], ["inline"], ["path"]
    remote: bool = True


@dataclass
class SourceDescriptor:
    """Public description of a source for discovery endpoints (GET /sources)."""
    id: str
    display_name: str
    capabilities: SourceCapabilities


class StructureSource(Protocol):
    id: str
    display_name: str
    capabilities: SourceCapabilities

    def supports(self, request: SourceRequest) -> bool: ...
    def fetch(self, request: SourceRequest) -> RawStructure: ...
    def fetch_metadata(self, identifier: str) -> StructureMetadata: ...

    def describe(self) -> SourceDescriptor: ...


__all__ = [
    "StructureSource", "SourceRequest", "RawStructure", "SourceCapabilities",
    "SourceDescriptor", "SourceError", "SourceNotFound",
]
