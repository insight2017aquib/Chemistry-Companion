"""
P2 API tests for the PAMS router.

Uses FastAPI dependency override to inject a service backed by a FakeHttpClient
(offline RCSB) + filesystem store in a tmp dir + a fake analyzer — so the routes
are tested in isolation from the network and the docking pipeline.
"""

import json

import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.routes.proteins import get_service
from core.pams.asset_service import ProteinAssetService
from core.pams.store import FileSystemAssetStore
from core.pams.sources.registry import SourceRegistry
from core.pams.sources.rcsb import RCSBSource
from core.pams.sources.upload import UploadSource
from core.pams.sources.local import LocalFileSource
from core.pams.transport import FakeHttpClient, HttpResponse
from core.pams.models import StructureMetadata, ChainSummary

_PDB = (
    "ATOM      1  N   ALA A   1      11.000  11.000  11.000  1.00  0.00           N\n"
    "END\n"
)
_META = json.dumps({"struct": {"title": "TEST"}, "rcsb_entry_info": {"resolution_combined": [2.0]},
                    "exptl": [{"method": "X-RAY DIFFRACTION"}], "rcsb_accession_info": {}})


class _FakeAnalyzer:
    def analyze(self, structure_text, base=None):
        md = base or StructureMetadata()
        md.chains = [ChainSummary("A", 1, 1, True)]
        return md


@pytest.fixture
def client(tmp_path):
    http = FakeHttpClient()
    http.register("https://files.rcsb.org/download/4duh.pdb", HttpResponse(200, _PDB, "u"))
    http.register("https://data.rcsb.org/rest/v1/core/entry/4duh", HttpResponse(200, _META, "u"))
    http.register("https://files.rcsb.org/download/9zzz.pdb", HttpResponse(404, "", "u"))

    reg = SourceRegistry()
    reg.register(RCSBSource(http))
    reg.register(UploadSource())
    reg.register(LocalFileSource())
    svc = ProteinAssetService(reg, FileSystemAssetStore(str(tmp_path)), analyzer=_FakeAnalyzer())

    app.dependency_overrides[get_service] = lambda: svc
    yield TestClient(app)
    app.dependency_overrides.pop(get_service, None)


def test_list_sources(client):
    r = client.get("/api/proteins/sources")
    assert r.status_code == 200
    ids = {s["id"] for s in r.json()["sources"]}
    assert ids == {"rcsb", "upload", "local"}


def test_fetch_creates_asset(client):
    r = client.post("/api/proteins/fetch", json={"identifier": "4DUH", "source": "rcsb"})
    assert r.status_code == 200, r.text
    asset = r.json()["asset"]
    assert asset["provider"] == "rcsb" and asset["provider_ref"] == "4DUH"
    assert asset["metadata"]["title"] == "TEST"
    assert asset["metadata"]["chains"][0]["chain_id"] == "A"
    assert asset["lifecycle_stage"] == "analyzed"


def test_fetch_not_found(client):
    r = client.post("/api/proteins/fetch", json={"identifier": "9ZZZ", "source": "rcsb"})
    assert r.status_code == 404


def test_fetch_bad_id(client):
    r = client.post("/api/proteins/fetch", json={"identifier": "BADID", "source": "rcsb"})
    assert r.status_code == 400


def test_upload_then_get_and_structure(client):
    r = client.post("/api/proteins/upload", json={"pdb_text": _PDB, "name": "mine"})
    assert r.status_code == 200
    aid = r.json()["asset"]["asset_id"]

    r2 = client.get(f"/api/proteins/{aid}")
    assert r2.status_code == 200 and r2.json()["asset"]["origin"] == "upload"

    r3 = client.get(f"/api/proteins/{aid}/structure")
    assert r3.status_code == 200 and r3.json()["pdb_text"].startswith("ATOM")

    r4 = client.get("/api/proteins")
    assert any(a["asset_id"] == aid for a in r4.json()["assets"])


def test_ai_context_endpoint(client):
    aid = client.post("/api/proteins/upload", json={"pdb_text": _PDB}).json()["asset"]["asset_id"]
    r = client.get(f"/api/proteins/{aid}/ai_context")
    assert r.status_code == 200
    assert r.json()["schema_version"] >= 1 and "chains" in r.json()


def test_get_unknown_asset_404(client):
    assert client.get("/api/proteins/does-not-exist").status_code == 404


def test_api_does_not_leak_filesystem_paths(client):
    """Tier-1 fix #5: artifact responses expose a URL, never an internal local path."""
    asset = client.post("/api/proteins/upload", json={"pdb_text": _PDB, "name": "x"}).json()["asset"]
    assert asset["artifacts"], "expected at least the source_structure artifact"
    for art in asset["artifacts"]:
        assert "ref" not in art                       # no local filesystem path
        assert art["url"].startswith("/api/proteins/")  # retrievable by URL instead
    # The same holds for the GET/list endpoints.
    got = client.get(f"/api/proteins/{asset['asset_id']}").json()["asset"]
    assert all("ref" not in a and "url" in a for a in got["artifacts"])
