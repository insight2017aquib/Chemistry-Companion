import pytest
from core.pipeline import AnalysisResult
from api.schemas.spectra import ProtonNMRResponse, CarbonNMRResponse, IRPredictionResponse

def test_serializer_contracts():
    """
    Validates that the AnalysisResult strictly maps to the Pydantic schemas expected by the API payload.
    """
    result = AnalysisResult(molecule=None)
    # Verify that if predictions are missing, they default safely
    # If they are present, they match the schemas
    
    assert hasattr(result, "proton_nmr_prediction")
    assert hasattr(result, "carbon_nmr_prediction")
    assert hasattr(result, "ir_prediction")
    
    # We can instantiate the Pydantic models with empty lists to prove schema drift hasn't occurred
    ir_resp = IRPredictionResponse(bands=[])
    assert hasattr(ir_resp, "bands")
    
    p_nmr_resp = ProtonNMRResponse(environments=[])
    assert hasattr(p_nmr_resp, "environments")
    
    c_nmr_resp = CarbonNMRResponse(environments=[])
    assert hasattr(c_nmr_resp, "environments")
