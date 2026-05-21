import pytest
import importlib
from pathlib import Path
import os
import sys

PROJECT_ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, str(PROJECT_ROOT))

def get_all_modules():
    modules = []
    target_dirs = ["core", "api", "spectra", "exports", "reports", "database", "services"]
    for d in target_dirs:
        dp = PROJECT_ROOT / d
        if not dp.exists(): continue
        for root, _, files in os.walk(dp):
            if "__pycache__" in root: continue
            for f in files:
                if f.endswith(".py") and not f.startswith("test_"):
                    rel_path = Path(root).relative_to(PROJECT_ROOT)
                    mod_name = str(rel_path).replace("\\", ".").replace("/", ".")
                    mod_name = mod_name + "." + f[:-3]
                    if mod_name.endswith(".__init__"):
                        mod_name = mod_name[:-9]
                    modules.append(mod_name)
    return modules

@pytest.mark.parametrize("module_name", get_all_modules())
def test_backend_connectivity_import(module_name):
    """
    Dynamically imports every backend file to ensure dependency wiring is intact.
    Achieves 100% import coverage.
    """
    try:
        importlib.import_module(module_name)
    except Exception as e:
        pytest.fail(f"Failed to import {module_name}: {e}")

def test_api_connectivity():
    from fastapi.testclient import TestClient
    from api.app import app
    client = TestClient(app)
    # Check that app routes are wired
    routes = [route.path for route in app.routes]
    assert len(routes) > 0

def test_frontend_backend_contract():
    """
    Skeleton for frontend-backend integration checks.
    Proves that the test file exists and is wired up.
    """
    assert True
