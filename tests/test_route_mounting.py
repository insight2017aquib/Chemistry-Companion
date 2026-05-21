import pytest
from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

def test_api_analyse_route_mounted():
    # We should get a valid JSON response or HTTP 422 if payload is missing, but NOT 404
    response = client.post("/api/analyse", json={})
    assert response.status_code != 404
    
def test_api_batch_route_mounted():
    response = client.post("/api/batch", json={})
    assert response.status_code != 404
    
def test_api_batch_process_route_mounted():
    response = client.post("/api/batch/process")
    assert response.status_code != 404
    
def test_dashboard_analyse_mounted():
    # The /analyse HTML endpoint
    response = client.post("/analyse")
    assert response.status_code != 404
    
def test_validation_run_mounted():
    response = client.post("/api/validation/run", json={})
    assert response.status_code != 404
    
def test_benchmarks_run_mounted():
    response = client.post("/api/benchmarks/run", json={})
    assert response.status_code != 404
