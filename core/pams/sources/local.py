"""
core/pams/sources/local.py
=========================
Local file source — ingest a structure from a path on disk as a StructureSource.
Proves the adapter model covers local files with no special-casing elsewhere.
"""

from __future__ import annotations

import os

from core.pams.models import StructureMetadata
from core.pams.sources.base import (
    SourceRequest, RawStructure, SourceCapabilities, SourceDescriptor,
    SourceError, SourceNotFound,
)

_ALLOWED_EXT = {".pdb", ".ent", ".cif", ".mmcif", ".pdbqt"}


class LocalFileSource:
    id = "local"
    display_name = "Local File"

    def __init__(self) -> None:
        self.capabilities = SourceCapabilities(
            formats=["pdb", "cif"], has_metadata=False, id_kinds=["path"], remote=False,
        )

    def supports(self, request: SourceRequest) -> bool:
        if request.source == self.id:
            return bool(request.path)
        return (
            request.source is None
            and request.path is not None
            and request.inline_text is None
            and request.identifier is None
        )

    def fetch(self, request: SourceRequest) -> RawStructure:
        path = request.path or ""
        if not path:
            raise SourceError("Local source requires a 'path'.")
        ext = os.path.splitext(path)[1].lower()
        if ext not in _ALLOWED_EXT:
            raise SourceError(f"Unsupported local structure extension: '{ext}'.")
        if not os.path.isfile(path):
            raise SourceNotFound(f"Local file not found: {path}")
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        if not text.strip():
            raise SourceError(f"Local file is empty: {path}")
        fmt = "cif" if ext in (".cif", ".mmcif") else "pdb"
        return RawStructure(
            text=text,
            fmt=fmt,
            provider=self.id,
            provider_ref=os.path.basename(path),
            source_url=None,
            name=os.path.splitext(os.path.basename(path))[0],
            metadata=StructureMetadata(),
        )

    def fetch_metadata(self, identifier: str) -> StructureMetadata:  # noqa: ARG002
        return StructureMetadata()

    def describe(self) -> SourceDescriptor:
        return SourceDescriptor(id=self.id, display_name=self.display_name,
                                capabilities=self.capabilities)


__all__ = ["LocalFileSource"]
