"""
Isolated tests for the PAMS core (P1).

Every layer is tested without network, without docking, and without a DB:
  * models: serialization round-trip, extension points, AI projection
  * sources: RCSB (FakeHttpClient), Upload, Local; registry resolve/autodetect
  * store: FileSystemAssetStore round-trip + artifacts + list
  * service: upload + fetch converge; injected analyzer shares one workflow
  * import-lint: PAMS core never imports the docking pipeline
"""

import json
import os

import pytest

from core.pams.models import (
    ProteinAsset, StructureMetadata, Artifact, Annotation, ChainSummary, LigandSummary,
    Origin, LifecycleStage, ArtifactKind,
)
from core.pams.transport import FakeHttpClient, HttpResponse, TransportError
from core.pams.sources.base import SourceRequest, SourceError, SourceNotFound
from core.pams.sources.rcsb import RCSBSource, is_pdb_id
from core.pams.sources.upload import UploadSource
from core.pams.sources.local import LocalFileSource
from core.pams.sources.registry import SourceRegistry
from core.pams.store import FileSystemAssetStore
from core.pams.asset_service import ProteinAssetService


# ── Fixtures ─────────────────────────────────────────────────────────

_PDB = (
    "ATOM      1  N   ALA A   1      11.000  11.000  11.000  1.00  0.00           N\n"
    "ATOM      2  CA  ALA A   1      12.000  11.000  11.000  1.00  0.00           C\n"
    "HETATM    3  C1  LIG A 900       0.000   0.000   0.000  1.00  0.00           C\n"
    "END\n"
)

_RCSB_META = json.dumps({
    "struct": {"title": "CRYSTAL STRUCTURE OF TEST"},
    "rcsb_entry_info": {"resolution_combined": [2.1]},
    "exptl": [{"method": "X-RAY DIFFRACTION"}],
    "rcsb_accession_info": {"initial_release_date": "2012-01-01"},
})


def _rcsb_http():
    http = FakeHttpClient()
    http.register("https://files.rcsb.org/download/4duh.pdb", HttpResponse(200, _PDB, "u"))
    http.register("https://data.rcsb.org/rest/v1/core/entry/4duh", HttpResponse(200, _RCSB_META, "u"))
    return http


# ── Models ───────────────────────────────────────────────────────────

def test_asset_roundtrip_serialization():
    a = ProteinAsset(name="4DUH", origin=Origin.FETCH.value, provider="rcsb", provider_ref="4DUH")
    a.metadata = StructureMetadata(title="t", resolution=2.1, chains=[ChainSummary("A", 10, 10, True)],
                                   ligands=[LigandSummary("LIG", "A", 900, 1)])
    a.add_artifact(Artifact(kind=ArtifactKind.SOURCE_STRUCTURE, ref="/x.pdb", format="pdb"))
    a.add_annotation(Annotation(kind="pocket", producer="fpocket", selection={"chain": "A"}))
    restored = ProteinAsset.from_dict(a.to_dict())
    assert restored.name == "4DUH"
    assert restored.metadata.chains[0].chain_id == "A"
    assert restored.get_artifact(ArtifactKind.SOURCE_STRUCTURE).ref == "/x.pdb"
    assert restored.annotations[0].kind == "pocket"


def test_add_artifact_is_idempotent_per_kind():
    a = ProteinAsset(name="x", origin=Origin.UPLOAD.value)
    a.add_artifact(Artifact(kind="receptor_pdbqt", ref="/a"))
    a.add_artifact(Artifact(kind="receptor_pdbqt", ref="/b"))
    assert len([x for x in a.artifacts if x.kind == "receptor_pdbqt"]) == 1
    assert a.get_artifact("receptor_pdbqt").ref == "/b"


def test_ai_context_is_stable_projection():
    a = ProteinAsset(name="4DUH", origin=Origin.FETCH.value, provider="rcsb", provider_ref="4DUH")
    a.metadata = StructureMetadata(title="T", ligands=[LigandSummary("LIG", "A", 900, 12)])
    ctx = a.to_ai_context()
    assert ctx["schema_version"] >= 1
    assert ctx["identity"]["provider"] == "rcsb"
    assert ctx["ligands"][0]["resname"] == "LIG"
    # AI projection must not leak internal store refs / raw vendor payloads
    assert "artifacts" not in ctx and "raw" not in ctx.get("structure", {})


# ── Sources ──────────────────────────────────────────────────────────

def test_rcsb_id_validation():
    assert is_pdb_id("4DUH") and is_pdb_id("1crn")
    assert not is_pdb_id("DUH") and not is_pdb_id("ABCD") and not is_pdb_id("12345")


def test_rcsb_fetch_with_fake_http():
    src = RCSBSource(_rcsb_http())
    raw = src.fetch(SourceRequest(source="rcsb", identifier="4DUH"))
    assert raw.provider == "rcsb" and raw.provider_ref == "4DUH"
    assert raw.text.startswith("ATOM")
    assert raw.metadata.title == "CRYSTAL STRUCTURE OF TEST"
    assert raw.metadata.resolution == 2.1
    assert raw.metadata.method == "X-RAY DIFFRACTION"


def test_rcsb_not_found():
    http = FakeHttpClient({"https://files.rcsb.org/download/9zzz.pdb": HttpResponse(404, "", "u")})
    with pytest.raises(SourceNotFound):
        RCSBSource(http).fetch(SourceRequest(source="rcsb", identifier="9ZZZ"))


def test_rcsb_rejects_bad_id_before_network():
    http = FakeHttpClient()   # no registered URLs → any call raises
    with pytest.raises(SourceError):
        RCSBSource(http).fetch(SourceRequest(source="rcsb", identifier="BADID"))
    assert http.calls == []   # proves validation happened before any request


def test_upload_source():
    raw = UploadSource().fetch(SourceRequest(source="upload", inline_text=_PDB, name="mine"))
    assert raw.provider == "upload" and raw.text == _PDB and raw.name == "mine"


def test_local_source(tmp_path):
    p = tmp_path / "s.pdb"
    p.write_text(_PDB, encoding="utf-8")
    raw = LocalFileSource().fetch(SourceRequest(source="local", path=str(p)))
    assert raw.provider == "local" and raw.text.startswith("ATOM")


def test_registry_autodetect():
    reg = SourceRegistry()
    reg.register(RCSBSource(_rcsb_http()))
    reg.register(UploadSource())
    reg.register(LocalFileSource())
    assert reg.resolve(SourceRequest(identifier="4DUH")).id == "rcsb"
    assert reg.resolve(SourceRequest(inline_text=_PDB)).id == "upload"
    assert reg.resolve(SourceRequest(path="/tmp/x.pdb")).id == "local"
    assert {d.id for d in reg.list()} == {"rcsb", "upload", "local"}


# ── Store ────────────────────────────────────────────────────────────

def test_filesystem_store_roundtrip(tmp_path):
    store = FileSystemAssetStore(str(tmp_path))
    a = ProteinAsset(name="4DUH", origin=Origin.FETCH.value, provider="rcsb", provider_ref="4DUH")
    store.save(a, _PDB, ArtifactKind.SOURCE_STRUCTURE)
    got = store.get(a.asset_id)
    assert got is not None and got.name == "4DUH"
    assert got.checksum is not None
    assert store.get_artifact_text(a.asset_id, ArtifactKind.SOURCE_STRUCTURE) == _PDB
    assert any(x.asset_id == a.asset_id for x in store.list())


def test_store_put_extra_artifact(tmp_path):
    store = FileSystemAssetStore(str(tmp_path))
    a = ProteinAsset(name="x", origin=Origin.UPLOAD.value)
    store.save(a, _PDB, ArtifactKind.SOURCE_STRUCTURE)
    store.put_artifact(a, ArtifactKind.RECEPTOR_PDBQT, "REMARK pdbqt\n", fmt="pdbqt", produced_by="prep")
    assert store.get_artifact_text(a.asset_id, ArtifactKind.RECEPTOR_PDBQT).startswith("REMARK")


# ── Service (convergence + shared analysis) ──────────────────────────

class _FakeAnalyzer:
    """Stand-in StructureAnalyzer so the service is testable without docking."""
    def __init__(self):
        self.calls = 0

    def analyze(self, structure_text, base=None):
        self.calls += 1
        md = base or StructureMetadata()
        md.chains = [ChainSummary("A", 1, 1, True)]
        md.ligands = [LigandSummary("LIG", "A", 900, 1)]
        return md


def _service(tmp_path, analyzer=None):
    reg = SourceRegistry()
    reg.register(RCSBSource(_rcsb_http()))
    reg.register(UploadSource())
    reg.register(LocalFileSource())
    return ProteinAssetService(reg, FileSystemAssetStore(str(tmp_path)), analyzer=analyzer)


def test_fetch_creates_asset_with_metadata(tmp_path):
    svc = _service(tmp_path, _FakeAnalyzer())
    asset = svc.fetch("4DUH", source="rcsb")
    assert asset.provider == "rcsb" and asset.provider_ref == "4DUH"
    assert asset.origin == Origin.FETCH.value
    assert asset.metadata.title == "CRYSTAL STRUCTURE OF TEST"   # from source
    assert asset.metadata.chains[0].chain_id == "A"             # from analyzer
    assert asset.lifecycle_stage == LifecycleStage.ANALYZED.value
    # structure retrievable via the store
    assert svc.get_structure_text(asset.asset_id).startswith("ATOM")


def test_upload_and_fetch_share_same_workflow(tmp_path):
    analyzer = _FakeAnalyzer()
    svc = _service(tmp_path, analyzer)
    fetched = svc.fetch("4DUH", source="rcsb")
    uploaded = svc.create_from_upload(_PDB, name="mine")
    # Both converged through the same analysis path.
    assert analyzer.calls == 2
    assert uploaded.origin == Origin.UPLOAD.value and uploaded.provider is None
    assert fetched.metadata.chains and uploaded.metadata.chains
    assert {a.asset_id for a in svc.list()} == {fetched.asset_id, uploaded.asset_id}


def test_service_without_analyzer_still_stores(tmp_path):
    svc = _service(tmp_path, analyzer=None)
    asset = svc.create_from_upload(_PDB, name="x")
    assert asset.lifecycle_stage == LifecycleStage.VALIDATED.value  # no analysis stage
    assert svc.get_structure_text(asset.asset_id) == _PDB


# ── Import-lint: PAMS core must not depend on the docking pipeline ───

def test_pams_core_has_no_docking_imports():
    """AST-level guard: no module under core/pams may IMPORT the docking pipeline.
    (Docstrings mentioning docking are fine — only real import statements count.)"""
    import ast
    import pathlib

    core_dir = pathlib.Path(__file__).resolve().parents[1] / "core" / "pams"
    banned = ("docking_workflow", "services.docking")
    offenders = []

    for py in core_dir.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            if any(n.startswith(banned) for n in names):
                offenders.append(f"{py.name}:{getattr(node, 'lineno', '?')}")

    assert offenders == [], f"PAMS core must stay docking-free, but these IMPORT docking: {offenders}"
