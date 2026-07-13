"""
Tests for asset-native docking (#4): resolving structure from an asset_id and
writing the prepared receptor back onto the ProteinAsset.
"""

from core.pams.asset_service import ProteinAssetService
from core.pams.store import FileSystemAssetStore
from core.pams.sources.registry import SourceRegistry
from core.pams.sources.upload import UploadSource
from core.pams.models import ArtifactKind, LifecycleStage, PreparationStatus

import api.routes.docking_workspace as dw

_PDB = "ATOM      1  N   ALA A   1      11.000  11.000  11.000  1.00  0.00           N\nEND\n"
_PDBQT = "REMARK receptor\nATOM      1  N   ALA A   1      11.000  11.000  11.000  1.00  0.00     0.000 N\n"


def _service(tmp_path):
    reg = SourceRegistry()
    reg.register(UploadSource())
    return ProteinAssetService(reg, FileSystemAssetStore(str(tmp_path)))


# ── PAMS core: write-back ────────────────────────────────────────────

def test_attach_prepared_receptor_advances_lifecycle(tmp_path):
    svc = _service(tmp_path)
    asset = svc.create_from_upload(_PDB, name="x")
    assert asset.preparation.docking_ready is False

    updated = svc.attach_prepared_receptor(asset.asset_id, _PDBQT, options={"remove_ligands": True})
    assert updated is not None
    assert updated.lifecycle_stage == LifecycleStage.DOCKING_READY.value
    assert updated.preparation.status == PreparationStatus.READY.value
    assert updated.preparation.docking_ready is True
    assert updated.preparation.options == {"remove_ligands": True}
    # The prepared receptor is retrievable as an artifact.
    assert svc.get_structure_text(asset.asset_id, ArtifactKind.RECEPTOR_PDBQT) == _PDBQT
    # ...and it did not clobber the original source structure.
    assert svc.get_structure_text(asset.asset_id, ArtifactKind.SOURCE_STRUCTURE) == _PDB


def test_attach_prepared_receptor_unknown_asset_returns_none(tmp_path):
    assert _service(tmp_path).attach_prepared_receptor("nope", _PDBQT) is None


# ── Docking route helpers: resolve + writeback ───────────────────────

class _FakeSvc:
    def __init__(self):
        self.attached = []

    def get_structure_text(self, asset_id, artifact_kind=None):
        return _PDB if asset_id == "known" else None

    def attach_prepared_receptor(self, asset_id, pdbqt, options=None):
        self.attached.append((asset_id, pdbqt, options))
        return object()


def test_resolve_prefers_pdb_text(monkeypatch):
    monkeypatch.setattr(dw, "_pams_service", lambda: _FakeSvc())
    assert dw._resolve_structure_text("EXPLICIT", "known") == "EXPLICIT"


def test_resolve_falls_back_to_asset(monkeypatch):
    monkeypatch.setattr(dw, "_pams_service", lambda: _FakeSvc())
    assert dw._resolve_structure_text("", "known").startswith("ATOM")


def test_resolve_empty_when_nothing_available(monkeypatch):
    monkeypatch.setattr(dw, "_pams_service", lambda: _FakeSvc())
    assert dw._resolve_structure_text("", "unknown") == ""
    assert dw._resolve_structure_text("", None) == ""


def test_writeback_is_best_effort(monkeypatch):
    fake = _FakeSvc()
    monkeypatch.setattr(dw, "_pams_service", lambda: fake)
    dw._writeback_prepared_receptor("known", _PDBQT, options={"a": 1})
    assert fake.attached == [("known", _PDBQT, {"a": 1})]
    # No asset_id or empty pdbqt → no-op, no error.
    dw._writeback_prepared_receptor(None, _PDBQT)
    dw._writeback_prepared_receptor("known", "")
    assert len(fake.attached) == 1


def test_writeback_swallows_service_errors(monkeypatch):
    class _Boom:
        def attach_prepared_receptor(self, *a, **k):
            raise RuntimeError("store down")
    monkeypatch.setattr(dw, "_pams_service", lambda: _Boom())
    # Must not raise — preparation should never be broken by a PAMS write-back failure.
    dw._writeback_prepared_receptor("known", _PDBQT)
