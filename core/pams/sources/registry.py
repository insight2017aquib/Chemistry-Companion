"""
core/pams/sources/registry.py
============================
Registry of structure-source plugins.

The registry is the single extension point: register an adapter and it becomes
available to resolve by id or auto-detect from a request. Nothing else changes.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from core.pams.sources.base import (
    StructureSource, SourceRequest, SourceDescriptor, SourceError,
)


class SourceRegistry:
    def __init__(self) -> None:
        self._sources: Dict[str, StructureSource] = {}

    def register(self, source: StructureSource) -> None:
        self._sources[source.id] = source

    def get(self, source_id: str) -> Optional[StructureSource]:
        return self._sources.get(source_id)

    def resolve(self, request: SourceRequest) -> StructureSource:
        """Pick the adapter for a request: explicit ``source`` wins; otherwise the
        first registered adapter that ``supports`` it."""
        if request.source:
            src = self._sources.get(request.source)
            if src is None:
                raise SourceError(f"Unknown structure source: '{request.source}'.")
            if not src.supports(request):
                raise SourceError(
                    f"Source '{request.source}' does not support this request."
                )
            return src

        for src in self._sources.values():
            if src.supports(request):
                return src
        raise SourceError("No registered source can handle this request.")

    def list(self) -> List[SourceDescriptor]:
        return [s.describe() for s in self._sources.values()]


__all__ = ["SourceRegistry"]
