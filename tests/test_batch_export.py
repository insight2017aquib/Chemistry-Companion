import pytest
from exports.schemas.batch_export_schema import build_batch_export_payload

def test_batch_export_survives_partial():
    # Mock data resembling a partial failure where descriptors are there, but ir is missing
    mock_results = [{
        "input": {"smiles": "CCO", "name": "Ethanol"},
        "success": True,
        "molecule": {"smiles": "CCO", "name": "Ethanol", "mol_weight": 46.0},
        "descriptors": {"logp": -0.31, "tpsa": 20.2},
        "functional_groups": {"hydroxyl": 1},
        "ir_prediction": None, # Partial failure
        "proton_nmr_prediction": None,
        "carbon_nmr_prediction": None,
    }]
    
    payload = build_batch_export_payload(mock_results)
    rows = payload.summary_rows()
    
    assert len(rows) == 1
    assert rows[0]["status"] == "partial"
    assert "Missing subsystems" in rows[0]["error"]
    
def test_batch_export_survives_failure():
    mock_results = [{
        "input": {"smiles": "INVALID"},
        "success": False,
        "error": "Failed to parse SMILES"
    }]
    
    payload = build_batch_export_payload(mock_results)
    rows = payload.summary_rows()
    
    assert len(rows) == 1
    assert rows[0]["status"] == "failed"
    assert rows[0]["error"] == "Failed to parse SMILES"
