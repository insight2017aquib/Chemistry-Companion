import pytest
from services.batch_service import BatchService

def test_batch_processes_valid_and_invalid():
    service = BatchService(max_workers=2)
    molecules = [
        {"smiles": "CCO", "name": "Ethanol"},
        {"smiles": "INVALID_SMILES_XXXX", "name": "Invalid"},
        {"smiles": "C1=CC=CC=C1", "name": "Benzene"}
    ]
    
    result = service.process_batch(molecules, include_spectra=False)
    
    assert result["total_molecules"] == 3
    assert result["successful_analyses"] == 2
    assert result["failed_analyses"] == 1
    
    res = result["results"]
    assert res[0]["success"] is True
    assert res[1]["success"] is False
    assert "error" in res[1]
    assert res[2]["success"] is True
