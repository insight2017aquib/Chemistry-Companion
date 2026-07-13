"""PAMS structure source adapters. Each provider is one module implementing the
StructureSource contract; add a provider by adding a module and registering it."""

from core.pams.sources.base import (
    StructureSource, SourceRequest, RawStructure, SourceCapabilities,
    SourceDescriptor, SourceError, SourceNotFound,
)
from core.pams.sources.registry import SourceRegistry
from core.pams.sources.rcsb import RCSBSource
from core.pams.sources.upload import UploadSource
from core.pams.sources.local import LocalFileSource

__all__ = [
    "StructureSource", "SourceRequest", "RawStructure", "SourceCapabilities",
    "SourceDescriptor", "SourceError", "SourceNotFound", "SourceRegistry",
    "RCSBSource", "UploadSource", "LocalFileSource",
]
