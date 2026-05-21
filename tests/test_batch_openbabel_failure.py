import pytest
from unittest.mock import patch
from services.batch_service import BatchService
from api.routes.batch import _format_batch_response

@patch("core.openbabel_utils._HAS_OPENBABEL", False)
def test_batch_survives_openbabel_failure():
    service = BatchService(max_workers=1)
    # Even if openbabel fails, the pipeline should run RDKit descriptors
    molecules = [{"smiles": "CCO", "name": "Ethanol"}]
    
    result = service.process_batch(molecules, include_spectra=True)
    
    # _format_batch_response should parse this as success because open babel isn't strictly required
    # for CCO, but it shouldn't crash!
    response = _format_batch_response(result)
    
    assert response.total == 1
    assert response.successful == 1
    assert response.failed == 0

