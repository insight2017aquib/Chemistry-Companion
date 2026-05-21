"""FastAPI endpoint and template integration tests."""

from __future__ import annotations

import io
import json

import pytest
from fastapi.testclient import TestClient

from api.app import app


@pytest.fixture
def client():
  with TestClient(app) as c:
    yield c


def test_health(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_dashboard_page(client: TestClient):
    r = client.get("/")
    assert r.status_code == 200
    assert "Workbench" in r.text
    assert "hx-post=\"/analyse\"" in r.text


def test_new_pages(client: TestClient):
    for path in ("/exports", "/validation", "/settings", "/docs", "/spectra"):
        r = client.get(path)
        assert r.status_code == 200, path


def test_batch_page(client: TestClient):
    r = client.get("/batch")
    assert r.status_code == 200
    assert "Batch Analysis" in r.text


def test_history_page(client: TestClient):
    r = client.get("/history")
    assert r.status_code == 200
    assert "Molecule History" in r.text


def test_analyze_benzene(client: TestClient):
    payload = {
        "molecule": {"smiles": "c1ccccc1", "name": "Benzene"},
        "include_spectra": True,
        "save_history": False,
    }
    r = client.post("/api/analyze", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["molecule"]["smiles"]
    assert data["descriptors"]["formula"]
    assert data["status"] == "success"


def test_analyse_alias(client: TestClient):
    payload = {
        "molecule": {"smiles": "CCO", "name": "Ethanol"},
        "include_spectra": False,
        "save_history": False,
    }
    r = client.post("/api/analyse", json=payload)
    assert r.status_code == 200


def test_funcgroups(client: TestClient):
    payload = {"molecule": {"smiles": "CC(=O)O"}, "include_spectra": False}
    r = client.post("/api/funcgroups", json=payload)
    assert r.status_code == 200
    assert "functional_group_report" in r.json()


def test_structure_png(client: TestClient):
    r = client.get("/api/structure.png", params={"smiles": "c1ccccc1", "width": 200, "height": 200})
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert len(r.content) > 100


def test_export_xlsx_profile(client: TestClient):
    analyze = client.post(
        "/api/analyze",
        json={"molecule": {"smiles": "c1ccccc1"}, "save_history": False},
    ).json()
    r = client.post(
        "/api/export",
        json={"data": analyze, "format": "xlsx", "profile": "medchem"},
    )
    assert r.status_code == 200
    assert "spreadsheet" in r.headers["content-type"]


def test_export_json(client: TestClient):
    analyze = client.post(
        "/api/analyze",
        json={"molecule": {"smiles": "c1ccccc1"}, "save_history": False},
    ).json()
    r = client.post("/api/export", json={"data": analyze, "format": "json"})
    assert r.status_code == 200
    assert "application/json" in r.headers["content-type"]


def test_batch_csv_upload(client: TestClient):
    csv_data = "smiles,name\nc1ccccc1,Benzene\nCCO,Ethanol\n"
    r = client.post(
        "/api/batch/upload",
        files={"file": ("mols.csv", io.BytesIO(csv_data.encode()), "text/csv")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    assert data["successful"] >= 1


def test_htmx_analyse(client: TestClient):
    r = client.post(
        "/analyse",
        data={
            "input_text": "c1ccccc1",
            "input_method": "smiles",
            "name": "Benzene",
            "include_spectra": "true",
        },
    )
    assert r.status_code == 200
    assert "Molecular Descriptors" in r.text or "Benzene" in r.text


def test_history_crud(client: TestClient):
    client.post(
        "/api/analyze",
        json={"molecule": {"smiles": "CCO", "name": "Ethanol"}, "save_history": True},
    )
    listed = client.get("/api/history").json()
    assert listed["count"] >= 1
    item_id = listed["items"][0]["id"]
    got = client.get(f"/api/history/{item_id}")
    assert got.status_code == 200
    deleted = client.delete(f"/api/history/{item_id}")
    assert deleted.status_code == 200
