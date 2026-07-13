import importlib.util
import sys
import types
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import only the docking_workspace route module without loading the full api.routes package
repo_root = Path(__file__).resolve().parents[1]
api_routes_path = str(repo_root / "api" / "routes")

import api  # load api package (lightweight)

# Stub services package and docking workspace service to avoid heavy core imports
if "services" not in sys.modules:
    services_pkg = types.ModuleType("services")
    services_pkg.__path__ = [str(repo_root / "services")]
    sys.modules["services"] = services_pkg

service_module = types.ModuleType("services.docking_workspace_service")

class DockingWorkspaceService:
    @staticmethod
    def is_available() -> bool:
        return True

    @staticmethod
    def unavailable_message() -> str:
        return "Docking backend unavailable"

    @staticmethod
    def analyze_receptor(pdb_text: str):
        return {
            "chains": [{
                "chain_id": "A",
                "num_residues": 2,
                "num_standard_aa": 2,
                "first_resnum": 1,
                "last_resnum": 2,
                "num_hetero": 1,
                "hetero_names": ["ATP"],
                "num_waters": 1,
                "is_likely_protein": True,
                "sample_residues": ["ALA1", "GLY2"]
            }],
            "total_chains": 1,
            "total_residues": 2,
            "total_waters": 1,
            "total_hetero_groups": 1,
            "num_models": 1,
            "format_detected": "pdb",
            "recommendation": {"recommended_chain_ids": ["A"], "confidence": "high"},
            "ligands": [{"resname": "ATP", "chain_id": "A", "resnum": 200, "num_atoms": 10, "centroid": {"x": 0, "y": 0, "z": 0}}],
            "cofactors": [{"resname": "ATP", "chain_id": "A", "resnum": 200, "classification": "nucleotide", "status": "required"}],
            "metals": [],
            "resolution": 2.0,
            "experimental_method": "X-RAY",
            "has_biological_assembly": False,
            "missing_residues": [],
            "quality_score": 85.0,
            "quality_label": "Excellent",
        }

    @staticmethod
    def classify_waters(pdb_text: str):
        return {
            "waters": [{
                "chain_id": "A",
                "resnum": 3,
                "x": 0.0,
                "y": 0.0,
                "z": 0.0,
                "category": "active_site",
                "distance_to_site": 1.2,
                "recommendation": "keep",
                "reason": "Within 5.0Å of binding site"
            }],
            "summary": {"total_waters": 1, "active_site_waters": 1, "bulk_waters": 0, "recommended_keep": 1, "recommended_remove": 0},
            "total": 1
        }

    @staticmethod
    def detect_ligand_binding_sites(pdb_text: str):
        return [{
            "ligand_resname": "ATP",
            "ligand_chain": "A",
            "ligand_resnum": 200,
            "centroid": {"x": 1.0, "y": 2.0, "z": 3.0},
            "radius": 6.0,
            "nearby_residues": ["A:1", "A:2"],
            "suggested_grid": {
                "center_x": 1.0,
                "center_y": 2.0,
                "center_z": 3.0,
                "size_x": 20.0,
                "size_y": 20.0,
                "size_z": 20.0,
            },
            "confidence": "high",
        }]

    @staticmethod
    def detect_pockets(pdb_text: str):
        return {
            "pockets": [{
                "pocket_id": 1,
                "score": 12.5,
                "center": {"x": 1.0, "y": 2.0, "z": 3.0},
                "radius": 8.0,
                "volume": 300.0,
                "druggability_score": 0.72,
                "residue_ids": ["A:1"],
            }],
            "suggestions": [{
                "type": "predicted_pocket",
                "pocket_id": 1,
                "score": 12.5,
                "center": {"x": 1.0, "y": 2.0, "z": 3.0},
                "radius": 8.0,
                "suggested_grid": {
                    "center_x": 1.0,
                    "center_y": 2.0,
                    "center_z": 3.0,
                    "size_x": 22.0,
                    "size_y": 22.0,
                    "size_z": 22.0,
                },
                "label": "Pocket 1 (score: 12.50)",
            }],
            "count": 1,
            "tool_used": "fpocket",
            "message": None,
        }

    @staticmethod
    def get_quality_assessment(pdb_text: str):
        return {"score": 85.0, "label": "Excellent", "breakdown": {"resolution": 15}, "notes": ["Test quality assessment"]}

service_module.DockingWorkspaceService = DockingWorkspaceService
sys.modules["services.docking_workspace_service"] = service_module

if "api.routes" not in sys.modules:
    routes_pkg = types.ModuleType("api.routes")
    routes_pkg.__path__ = [api_routes_path]
    sys.modules["api.routes"] = routes_pkg

spec = importlib.util.spec_from_file_location(
    "api.routes.docking_workspace",
    repo_root / "api" / "routes" / "docking_workspace.py"
)
mod = importlib.util.module_from_spec(spec)
sys.modules["api.routes.docking_workspace"] = mod
spec.loader.exec_module(mod)

docking_router = mod.router
app = FastAPI()
app.include_router(docking_router, prefix="/api/docking")
client = TestClient(app)

SAMPLE_PDB = """
ATOM      1  N   ALA A   1      11.104  13.207  12.717  1.00 20.00           N
ATOM      2  CA  ALA A   1      12.050  14.132  12.190  1.00 20.00           C
ATOM      3  C   ALA A   1      13.334  13.451  11.780  1.00 20.00           C
ATOM      4  O   ALA A   1      14.281  14.129  11.525  1.00 20.00           O
ATOM      5  CB  ALA A   1      11.410  15.507  12.475  1.00 20.00           C
ATOM      6  N   GLY A   2      13.347  12.232  11.720  1.00 20.00           N
ATOM      7  CA  GLY A   2      14.516  11.445  11.424  1.00 20.00           C
ATOM      8  C   GLY A   2      15.677  12.219  11.025  1.00 20.00           C
ATOM      9  O   GLY A   2      16.638  11.634  10.800  1.00 20.00           O
HETATM   10  O   HOH A   3      15.856  13.594  12.238  1.00 20.00           O
HETATM   11  C   ATP A 200      15.856  13.594  12.238  1.00 20.00           C
END
"""


def test_protein_analysis_endpoints_exist_and_return_json():
    endpoints = [
        "/api/docking/protein/analyze",
        "/api/docking/protein/chains",
        "/api/docking/protein/waters",
        "/api/docking/protein/cofactors",
        "/api/docking/protein/metals",
        "/api/docking/protein/quality",
    ]

    for endpoint in endpoints:
        response = client.post(endpoint, json={"pdb_text": SAMPLE_PDB})
        assert response.status_code in {200, 400, 503}
        if response.status_code == 200:
            assert response.headers["content-type"].startswith("application/json")
            assert response.json() is not None


def test_protein_analyze_returns_chain_and_summary():
    response = client.post("/api/docking/protein/analyze", json={"pdb_text": SAMPLE_PDB})
    assert response.status_code == 200
    data = response.json()
    assert data["total_chains"] == 1
    assert data["total_residues"] >= 1
    assert "recommendation" in data


def test_protein_chain_summary_includes_ligand_and_waters():
    response = client.post("/api/docking/protein/chains", json={"pdb_text": SAMPLE_PDB})
    assert response.status_code == 200
    data = response.json()
    assert data["total_chains"] == 1
    assert data["chains"]
    assert data["chains"][0]["ligands"] == ["ATP"] or data["chains"][0]["ligands"] == []


def test_protein_quality_returns_score_and_label():
    response = client.post("/api/docking/protein/quality", json={"pdb_text": SAMPLE_PDB})
    assert response.status_code == 200
    data = response.json()
    assert "score" in data
    assert "label" in data
    assert isinstance(data["score"], (int, float))


def test_phase03_receptor_visualization_endpoints_return_sites_and_waters():
    ligand_sites = client.post("/api/docking/receptor/ligand_sites", json={"pdb_text": SAMPLE_PDB})
    assert ligand_sites.status_code == 200
    ligand_data = ligand_sites.json()
    assert ligand_data["count"] == 1
    assert ligand_data["sites"][0]["suggested_grid"]["size_x"] == 20.0

    pockets = client.post("/api/docking/receptor/pockets", json={"pdb_text": SAMPLE_PDB})
    assert pockets.status_code == 200
    pocket_data = pockets.json()
    assert pocket_data["count"] == 1
    assert pocket_data["suggestions"][0]["label"].startswith("Pocket 1")

    waters = client.post("/api/docking/receptor/waters", json={"pdb_text": SAMPLE_PDB})
    assert waters.status_code == 200
    water_data = waters.json()
    assert water_data["summary"]["active_site_waters"] == 1
