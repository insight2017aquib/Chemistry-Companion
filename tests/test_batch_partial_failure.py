import pytest
from unittest.mock import patch
from services.batch_service import BatchService
from api.routes.batch import _format_batch_response

@patch("core.pipeline.ChemistryPipeline._safe_predict")
def test_batch_partial_failure_contract(mock_safe_predict):
    def fake_predict(predictor, mol, label, warnings):
        warnings.append(f"Mocked {label} failure")
        return None
        
    mock_safe_predict.side_effect = fake_predict
    
    service = BatchService(max_workers=1)
    molecules = [{"smiles": "CCO", "name": "Ethanol"}]
    
    result = service.process_batch(molecules, include_spectra=True)
    
    response = _format_batch_response(result)
    assert response.partial == 1
    assert response.successful == 0
    
    row = response.results[0]
    assert row.status == "partial"
    
    assert "Mocked IR failure" in row.error
    assert "Missing subsystems: ir_prediction" in row.error
