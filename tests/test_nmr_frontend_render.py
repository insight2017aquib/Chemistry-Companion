
import pytest
from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

def test_frontend_render_null_safety():
    response = client.post('/api/analyse', data={
        'input_text': 'c1ccccc1'
    })
    html = response.text
    assert 'HEURISTIC' in html
    assert '7.' in html or '6.' in html
    assert '134.' in html or '122.' in html

