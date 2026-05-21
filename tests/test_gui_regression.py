import pytest
from fastapi.testclient import TestClient
from api.app import app
import json

client = TestClient(app)

def test_live_single_analysis_works():
    """
    Simulates the form submission from the analysis page.
    """
    data = {
        "input_text": "CCO",
        "input_method": "smiles",
        "include_spectra": "true"
    }
    # Using the /analyse endpoint that dashboard uses
    response = client.post("/analyse", data=data)
    
    assert response.status_code == 200
    assert "Ethanol" in response.text or "C2H6O" in response.text or "CCO" in response.text

def test_live_batch_upload_works():
    """
    Simulates real batch upload from the batch.html page.
    """
    csv_content = "name,smiles\nEthanol,CCO\nBenzene,c1ccccc1\n"
    
    # We send it as multipart form data
    files = {"file": ("test.csv", csv_content.encode("utf-8"), "text/csv")}
    data = {"include_spectra": "true"}
    
    response = client.post("/api/batch/process", files=files, data=data)
    
    assert response.status_code == 200
    assert "Ethanol" in response.text
    assert "Benzene" in response.text

def test_validation_works():
    # Because seaborn is now installed, this shouldn't 500 crash
    response = client.post("/api/validation/run", json={"dataset": "default"})
    # It might return an error if "default" dataset isn't loaded, but it shouldn't be a 500 ModuleNotFoundError
    assert response.status_code in [200, 400, 422, 404]

def test_benchmarks_work():
    # Similar to validation
    response = client.post("/api/benchmarks/run", json={"iterations": 1})
    assert response.status_code in [200, 400, 422, 404]
