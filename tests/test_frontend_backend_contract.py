"""
tests/test_frontend_backend_contract.py
=======================================
Verifies that serialized data correctly contains the fields the frontend expects.
"""

from core.molecule_utils import load_molecule
from core.pipeline import ChemistryPipeline
from api.serializers import serialize_analysis_result

def test_serialized_fields_for_frontend():
    pipeline = ChemistryPipeline()
    pipeline_result = pipeline.analyze(smiles="C=C")
    
    serialized = serialize_analysis_result(pipeline_result)
    
    # Check that required frontend components have their data
    assert "molecule" in serialized
    assert "descriptors" in serialized
    assert "functional_groups" in serialized
    assert "ir_prediction" in serialized
    assert "proton_nmr_prediction" in serialized
    assert "carbon_nmr_prediction" in serialized
    
    # 13C NMR fields expected by the accordion component
    cnmr = serialized["carbon_nmr_prediction"]
    assert "environments" in cnmr
    for env in cnmr["environments"]:
        # The template uses 'shift_ppm', 'ppm_range', 'carbon_count', 'label'
        assert "label" in env
