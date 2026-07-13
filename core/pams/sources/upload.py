"""
core/pams/sources/upload.py
==========================
Upload source — user-provided structure text as a first-class StructureSource.

Modeling uploads as an adapter (rather than a special case) is what lets uploaded
and fetched proteins share exactly the same downstream workflow: both produce a
RawStructure -> ProteinAsset through one path.
"""

from __future__ import annotations

from core.pams.models import StructureMetadata
from core.pams.sources.base import (
    SourceRequest, RawStructure, SourceCapabilities, SourceDescriptor, SourceError,
)


class UploadSource:
    id = "upload"
    display_name = "User Upload"

    def __init__(self) -> None:
        self.capabilities = SourceCapabilities(
            formats=["pdb", "cif"], has_metadata=False, id_kinds=["inline"], remote=False,
        )

    def supports(self, request: SourceRequest) -> bool:
        if request.source == self.id:
            return bool(request.inline_text)
        # auto-detect: inline text present, no remote identifier/path
        return (
            request.source is None
            and request.inline_text is not None
            and request.identifier is None
            and request.path is None
        )

    def fetch(self, request: SourceRequest) -> RawStructure:
        if not request.inline_text or not request.inline_text.strip():
            raise SourceError("Upload source requires non-empty inline_text.")
        return RawStructure(
            text=request.inline_text,
            fmt=(request.fmt or "pdb").lower(),
            provider=self.id,
            provider_ref=None,
            source_url=None,
            name=request.name or "uploaded_structure",
            metadata=StructureMetadata(),
        )

    def fetch_metadata(self, identifier: str) -> StructureMetadata:  # noqa: ARG002
        return StructureMetadata()

    def describe(self) -> SourceDescriptor:
        return SourceDescriptor(id=self.id, display_name=self.display_name,
                                capabilities=self.capabilities)


__all__ = ["UploadSource"]
