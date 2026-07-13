"""
api/routes/proteins.py
=====================
PAMS HTTP surface — protein-asset-centric and source-agnostic (P2).

Every protein (uploaded or fetched from any source) is a ProteinAsset. Mol*, the
UI, and future AI services consume assets through these endpoints — never loose
PDB files. Existing docking endpoints are untouched; docking reuses a fetched
structure via GET /api/proteins/{id}/structure (backward compatible).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.pams.models import ArtifactKind
from core.pams.sources.base import SourceError, SourceNotFound
from core.pams.transport import TransportError
from core.paths import pams_root

logger = logging.getLogger(__name__)

router = APIRouter()

_PAMS_ROOT = str(pams_root())


@lru_cache(maxsize=1)
def _default_service():
    """Lazily build the fully-wired PAMS service (sources + store + shared analyzer).
    Overridable in tests via `get_service` dependency override."""
    from core.pams_integrations import build_service
    return build_service(_PAMS_ROOT)


def get_service():
    """FastAPI dependency seam so tests can inject a fake service."""
    return _default_service()


# ── Request models ───────────────────────────────────────────────────

class FetchRequest(BaseModel):
    identifier: str
    source: Optional[str] = None      # None → auto-detect (e.g. 4-char id → RCSB)
    format: str = "pdb"


class UploadRequest(BaseModel):
    pdb_text: str
    name: Optional[str] = None


# ── Error mapping ────────────────────────────────────────────────────

def _handle(exc: Exception) -> HTTPException:
    if isinstance(exc, SourceNotFound):
        return HTTPException(404, str(exc))
    if isinstance(exc, SourceError):
        return HTTPException(400, str(exc))
    if isinstance(exc, TransportError):
        return HTTPException(502, f"Upstream structure source error: {exc}")
    return HTTPException(500, f"Protein asset operation failed: {exc}")


def _public_asset(asset) -> dict:
    """Serialize an asset for the API WITHOUT leaking internal storage paths.

    Each artifact's local ``ref`` (an absolute filesystem path) is replaced with a
    retrievable API URL, so the frontend/AI consumers reference artifacts by URL,
    never by server path."""
    d = asset.to_dict()
    for art in d.get("artifacts", []):
        art["url"] = f"/api/proteins/{d['asset_id']}/structure?artifact={art['kind']}"
        art.pop("ref", None)   # never expose local filesystem paths
    return d


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("/sources")
async def list_sources(svc=Depends(get_service)):
    """Discoverable list of available structure sources (drives the UI dropdown)."""
    return {
        "sources": [
            {
                "id": d.id,
                "display_name": d.display_name,
                "capabilities": {
                    "formats": d.capabilities.formats,
                    "has_metadata": d.capabilities.has_metadata,
                    "id_kinds": d.capabilities.id_kinds,
                    "remote": d.capabilities.remote,
                },
            }
            for d in svc.sources()
        ]
    }


@router.post("/fetch")
async def fetch_protein(req: FetchRequest, svc=Depends(get_service)):
    """Fetch a structure by identifier from a (possibly auto-detected) source and
    persist it as a ProteinAsset."""
    try:
        asset = svc.fetch(req.identifier.strip(), source=req.source, fmt=req.format)
        return {"asset": _public_asset(asset)}
    except Exception as exc:  # noqa: BLE001
        raise _handle(exc)


@router.post("/upload")
async def upload_protein(req: UploadRequest, svc=Depends(get_service)):
    """Create a ProteinAsset from user-provided structure text (additive; existing
    docking upload flow is unchanged)."""
    try:
        asset = svc.create_from_upload(req.pdb_text, name=req.name)
        return {"asset": _public_asset(asset)}
    except Exception as exc:  # noqa: BLE001
        raise _handle(exc)


@router.get("")
async def list_proteins(project_id: Optional[str] = None, svc=Depends(get_service)):
    """List protein assets (the PAMS library; optionally scoped to a project)."""
    try:
        return {"assets": [_public_asset(a) for a in svc.list(project_id=project_id)]}
    except Exception as exc:  # noqa: BLE001
        raise _handle(exc)


@router.get("/{asset_id}")
async def get_protein(asset_id: str, svc=Depends(get_service)):
    """Full ProteinAsset (metadata/artifacts/annotations)."""
    asset = svc.get(asset_id)
    if asset is None:
        raise HTTPException(404, f"No protein asset {asset_id}")
    return {"asset": _public_asset(asset)}


@router.get("/{asset_id}/ai_context")
async def get_protein_ai_context(asset_id: str, svc=Depends(get_service)):
    """Stable, versioned projection for AI services."""
    asset = svc.get(asset_id)
    if asset is None:
        raise HTTPException(404, f"No protein asset {asset_id}")
    return asset.to_ai_context()


@router.get("/{asset_id}/structure")
async def get_protein_structure(asset_id: str, artifact: str = ArtifactKind.SOURCE_STRUCTURE, svc=Depends(get_service)):
    """Return an artifact's structure text (Mol* and docking load by this reference,
    never by a loose file path)."""
    text = svc.get_structure_text(asset_id, artifact_kind=artifact)
    if text is None:
        raise HTTPException(404, f"No '{artifact}' structure for asset {asset_id}")
    return {"asset_id": asset_id, "artifact": artifact, "pdb_text": text}
