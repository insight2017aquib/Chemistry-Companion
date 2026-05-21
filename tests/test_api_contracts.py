"""
tests/test_api_contracts.py
===========================
Verifies that all API endpoints expected by the frontend exist and return the correct structures.
"""

from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

def test_docking_contract():
    response = client.post("/api/docking/generate", data={"input_text": "C", "ph": "7.4", "forcefield": "mmff94"})
    # It might fail due to lack of openbabel in test environment, but the contract should exist
    assert response.status_code == 200
    json_data = response.json()
    assert "success" in json_data
    assert "status" in json_data
    if json_data["success"]:
        assert "job_id" in json_data
        assert "download_url" in json_data

def test_validation_contract():
    # Avoid actually running full validation if it takes too long, but we check if the endpoint is there
    # For a contract test, we just want to ensure it doesn't 404 and returns JSON
    response = client.post("/api/validation/run")
    assert response.status_code == 200
    json_data = response.json()
    assert "success" in json_data
    assert "status" in json_data

def test_benchmarks_contract():
    response = client.post("/api/benchmarks/run")
    assert response.status_code == 200
    json_data = response.json()
    assert "success" in json_data
    assert "status" in json_data

def test_analysis_contract():
    response = client.post("/api/analyse", data={"input_text": "C", "input_type": "smiles"})
    assert response.status_code == 200
    # Expected to return HTML partials for analysis
    assert "text/html" in response.headers["content-type"]
