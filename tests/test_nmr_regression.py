
import pytest
from fastapi.testclient import TestClient
from api.app import app
import re

client = TestClient(app)

def test_nmr_regression_multiple_molecules():
    molecules = ['c1ccccc1', 'CCO', 'CC(=O)Oc1ccccc1C(=O)O', 'CN1C=NC2=C1C(=O)N(C(=O)N2C)C']
    for input_text in molecules:
        resp = client.post('/api/analyse', data={'input_text': input_text})
        assert resp.status_code == 200
        html = resp.text
        assert 'NMR' in html
        # Check for digits followed by a period, to ensure we rendered some ppm value
        assert re.search(r'\d+\.\d+', html) is not None

