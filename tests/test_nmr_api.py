
import pytest
from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

def test_analyze_api_nmr():
    response = client.post('/api/analyse', data={
        'input_text': 'c1ccccc1'
    })
    assert response.status_code == 200
    html = response.text
    assert 'HEURISTIC' in html
    assert 'NMR' in html

