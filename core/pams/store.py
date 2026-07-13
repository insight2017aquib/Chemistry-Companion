"""
core/pams/store.py
=================
Filesystem-backed AssetStore.

Layout (one directory per asset):
    <root>/<asset_id>/
        asset.json                 # serialized ProteinAsset
        <kind>.<ext>               # one file per artifact (source_structure.pdb, ...)

A SQL-backed AssetStore can replace this later with no change to callers, because
everything goes through the AssetStore port.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import List, Optional

from core.pams.models import ProteinAsset, Artifact


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _ext_for(fmt: str) -> str:
    return {"pdb": "pdb", "cif": "cif", "pdbqt": "pdbqt"}.get((fmt or "").lower(), "dat")


class FileSystemAssetStore:
    def __init__(self, root: str):
        self._root = root
        os.makedirs(self._root, exist_ok=True)

    # -- paths ----------------------------------------------------------------
    def _dir(self, asset_id: str) -> str:
        return os.path.join(self._root, asset_id)

    def _asset_json(self, asset_id: str) -> str:
        return os.path.join(self._dir(asset_id), "asset.json")

    def _artifact_path(self, asset_id: str, kind: str, fmt: str) -> str:
        return os.path.join(self._dir(asset_id), f"{kind}.{_ext_for(fmt)}")

    # -- port -----------------------------------------------------------------
    def save(self, asset: ProteinAsset, structure_text: str, artifact_kind: str) -> None:
        os.makedirs(self._dir(asset.asset_id), exist_ok=True)
        self.put_artifact(asset, artifact_kind, structure_text,
                          fmt=asset.primary_format, produced_by=asset.provider or asset.origin)
        if asset.checksum is None:
            asset.checksum = _sha256(structure_text)
        self._write_asset(asset)

    def put_artifact(self, asset: ProteinAsset, kind: str, text: str,
                     fmt: str = "", produced_by: str = "") -> None:
        os.makedirs(self._dir(asset.asset_id), exist_ok=True)
        fmt = fmt or asset.primary_format
        path = self._artifact_path(asset.asset_id, kind, fmt)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        asset.add_artifact(Artifact(
            kind=kind, ref=path, format=fmt, checksum=_sha256(text), produced_by=produced_by,
        ))
        self._write_asset(asset)

    def get(self, asset_id: str) -> Optional[ProteinAsset]:
        path = self._asset_json(asset_id)
        if not os.path.isfile(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return ProteinAsset.from_dict(json.load(f))

    def get_artifact_text(self, asset_id: str, artifact_kind: str) -> Optional[str]:
        asset = self.get(asset_id)
        if asset is None:
            return None
        art = asset.get_artifact(artifact_kind)
        if art is None or not os.path.isfile(art.ref):
            return None
        with open(art.ref, "r", encoding="utf-8") as f:
            return f.read()

    def list(self, project_id: Optional[str] = None) -> List[ProteinAsset]:
        assets: List[ProteinAsset] = []
        if not os.path.isdir(self._root):
            return assets
        for entry in os.listdir(self._root):
            path = self._asset_json(entry)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    asset = ProteinAsset.from_dict(json.load(f))
            except (ValueError, KeyError):
                continue
            if project_id is not None and asset.project_id != project_id:
                continue
            assets.append(asset)
        assets.sort(key=lambda a: a.created_at, reverse=True)
        return assets

    def delete(self, asset_id: str) -> bool:
        import shutil
        d = self._dir(asset_id)
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)
            return True
        return False

    # -- internal -------------------------------------------------------------
    def _write_asset(self, asset: ProteinAsset) -> None:
        asset.touch()
        with open(self._asset_json(asset.asset_id), "w", encoding="utf-8") as f:
            json.dump(asset.to_dict(), f, indent=2)


__all__ = ["FileSystemAssetStore"]
