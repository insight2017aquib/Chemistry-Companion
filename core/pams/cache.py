"""
core/pams/cache.py
=================
Structure download cache.

Remote sources (RCSB, AlphaFold, ...) fetch immutable structure files; a cache
avoids re-downloading the same entry on repeat fetches. The cache is a pluggable
port so it can be a no-op (tests), on-disk (default), or something else later.
"""

from __future__ import annotations

import hashlib
import os
from typing import Optional, Protocol


class StructureCache(Protocol):
    def get(self, key: str) -> Optional[str]: ...
    def put(self, key: str, text: str) -> None: ...


class NullStructureCache:
    """No-op cache (default when caching is disabled / in tests)."""

    def get(self, key: str) -> Optional[str]:
        return None

    def put(self, key: str, text: str) -> None:
        return None


class FileSystemStructureCache:
    """Simple on-disk cache keyed by an opaque string (hashed to a filename)."""

    def __init__(self, root: str):
        self._root = root
        os.makedirs(self._root, exist_ok=True)

    def _path(self, key: str) -> str:
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
        return os.path.join(self._root, f"{digest}.txt")

    def get(self, key: str) -> Optional[str]:
        path = self._path(key)
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            return None

    def put(self, key: str, text: str) -> None:
        try:
            with open(self._path(key), "w", encoding="utf-8") as f:
                f.write(text)
        except OSError:
            # Caching is best-effort; a write failure must never break a fetch.
            pass


__all__ = ["StructureCache", "NullStructureCache", "FileSystemStructureCache"]
