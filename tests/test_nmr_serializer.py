
import pytest
from core.pipeline import ChemistryPipeline
from api.serializers import serialize_analysis_result

def test_nmr_serializer():
    pipeline = ChemistryPipeline()
    result = pipeline.analyze(smiles='c1ccccc1')
    payload = serialize_analysis_result(result)
    
    assert 'proton_nmr_prediction' in payload
    p_nmr = payload['proton_nmr_prediction']
    assert 'signals' in p_nmr
    assert 'ppm_range' in p_nmr['signals'][0]
    assert 'disclaimer' in p_nmr
    
    assert 'carbon_nmr_prediction' in payload
    c_nmr = payload['carbon_nmr_prediction']
    assert 'environments' in c_nmr
    assert 'ppm_range' in c_nmr['environments'][0]
    assert 'disclaimer' in c_nmr
