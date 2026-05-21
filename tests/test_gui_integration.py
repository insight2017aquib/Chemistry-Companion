"""
tests/test_gui_integration.py
=============================
Tests the routing of GUI pages.
"""

from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

def test_gui_pages_exist():
    pages = [
        "/",
        "/analysis",
        "/batch",
        "/history",
        "/spectra",
        "/docking",
        "/validation",
        "/benchmarks",
        "/exports",
        "/settings"
    ]
    for page in pages:
        response = client.get(page)
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
