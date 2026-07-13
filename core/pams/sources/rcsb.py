"""
core/pams/sources/rcsb.py
========================
RCSB PDB structure source — THE ONLY module that knows RCSB specifics.

All RCSB URLs, ID rules, and JSON shapes are confined here. The rest of PAMS
refers to this source by its id ("rcsb") and the generic StructureSource contract.
"""

from __future__ import annotations

import re
from typing import Optional

from core.pams.models import StructureMetadata
from core.pams.transport import HttpClient, TransportError
from core.pams.cache import StructureCache, NullStructureCache
from core.pams.sources.base import (
    StructureSource, SourceRequest, RawStructure, SourceCapabilities,
    SourceDescriptor, SourceError, SourceNotFound,
)

_PDB_ID_RE = re.compile(r"^[0-9][A-Za-z0-9]{3}$")   # 4 chars, first is a digit
_STRUCTURE_URL = "https://files.rcsb.org/download/{id}.{ext}"
_METADATA_URL = "https://data.rcsb.org/rest/v1/core/entry/{id}"

# RCSB host knowledge lives here (and only here); the transport allowlist is
# populated from this so no vendor host is hardcoded elsewhere.
RCSB_HOSTS = frozenset({"files.rcsb.org", "data.rcsb.org"})


def is_pdb_id(value: str) -> bool:
    return bool(_PDB_ID_RE.match((value or "").strip()))


class RCSBSource:
    id = "rcsb"
    display_name = "RCSB PDB"
    allowed_hosts = RCSB_HOSTS

    def __init__(self, http: HttpClient, request_timeout: float = 30.0,
                 cache: StructureCache | None = None):
        self._http = http
        self._timeout = request_timeout
        self._cache = cache or NullStructureCache()
        self.capabilities = SourceCapabilities(
            formats=["pdb", "cif"], has_metadata=True, id_kinds=["pdb_id"], remote=True,
        )

    # -- contract -------------------------------------------------------------
    def supports(self, request: SourceRequest) -> bool:
        if request.source == self.id:
            return bool(request.identifier)
        # auto-detect: a bare 4-char PDB id with no inline/path payload
        return (
            request.source is None
            and request.identifier is not None
            and request.inline_text is None
            and request.path is None
            and is_pdb_id(request.identifier)
        )

    def fetch(self, request: SourceRequest) -> RawStructure:
        pdb_id = self._normalize_id(request.identifier)
        fmt = (request.fmt or "pdb").lower()
        ext = "cif" if fmt == "cif" else "pdb"
        url = _STRUCTURE_URL.format(id=pdb_id.lower(), ext=ext)

        cache_key = f"rcsb:{pdb_id}:{ext}"
        cached_text = self._cache.get(cache_key)
        from_cache = cached_text is not None

        if from_cache:
            structure_text = cached_text
        else:
            resp = self._http.get(url, timeout=self._timeout)
            if resp.status == 404:
                raise SourceNotFound(f"PDB id '{pdb_id}' not found at RCSB.")
            if not resp.ok:
                raise SourceError(f"RCSB returned HTTP {resp.status} for {pdb_id}.")
            if not resp.text.strip():
                raise SourceError(f"RCSB returned an empty structure for {pdb_id}.")
            structure_text = resp.text
            self._cache.put(cache_key, structure_text)

        metadata = None
        try:
            metadata = self.fetch_metadata(pdb_id)
        except (SourceError, TransportError):
            # Metadata is best-effort; the structure is the essential artifact.
            metadata = StructureMetadata(source_url=url)

        return RawStructure(
            text=structure_text,
            fmt="cif" if ext == "cif" else "pdb",
            provider=self.id,
            provider_ref=pdb_id,
            source_url=url,
            name=pdb_id,
            metadata=metadata,
            cached=from_cache,
            raw_metadata=(metadata.raw if metadata else {}),
        )

    def fetch_metadata(self, identifier: str) -> StructureMetadata:
        pdb_id = self._normalize_id(identifier)
        url = _METADATA_URL.format(id=pdb_id.lower())
        resp = self._http.get(url, timeout=self._timeout)
        if resp.status == 404:
            raise SourceNotFound(f"No RCSB metadata for '{pdb_id}'.")
        if not resp.ok:
            raise SourceError(f"RCSB metadata HTTP {resp.status} for {pdb_id}.")
        import json
        try:
            payload = json.loads(resp.text)
        except ValueError as exc:
            raise SourceError(f"Malformed RCSB metadata for {pdb_id}: {exc}") from exc
        return self._map_metadata(payload, url)

    def describe(self) -> SourceDescriptor:
        return SourceDescriptor(id=self.id, display_name=self.display_name,
                                capabilities=self.capabilities)

    # -- RCSB-specific mapping (kept private to this module) ------------------
    @staticmethod
    def _normalize_id(identifier: Optional[str]) -> str:
        if not identifier or not is_pdb_id(identifier):
            raise SourceError(f"'{identifier}' is not a valid 4-character PDB id.")
        return identifier.strip().upper()

    @staticmethod
    def _map_metadata(payload: dict, url: str) -> StructureMetadata:
        struct = payload.get("struct", {}) or {}
        entry_info = payload.get("rcsb_entry_info", {}) or {}
        exptl = payload.get("exptl", []) or []
        accession = payload.get("rcsb_accession_info", {}) or {}

        resolutions = entry_info.get("resolution_combined") or []
        resolution = resolutions[0] if resolutions else None
        method = exptl[0].get("method") if exptl and isinstance(exptl[0], dict) else None

        return StructureMetadata(
            title=struct.get("title"),
            resolution=resolution,
            method=method,
            deposited_date=accession.get("initial_release_date"),
            keywords=[],
            source_url=url,
            license="https://www.rcsb.org/pages/usage-policy",
            raw=payload,
        )


__all__ = ["RCSBSource", "is_pdb_id"]
