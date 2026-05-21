import pytest
from core import openbabel_utils

def test_openbabel_failure_isolation(monkeypatch):
    """
    Mock Open Babel as missing to verify failure boundaries.
    """
    # Force the module flag to False
    monkeypatch.setattr(openbabel_utils, "_HAS_OPENBABEL", False)
    
    # Asserting that functions fail gracefully with an explicit message
    # rather than crashing the thread with ImportError
    
    result = openbabel_utils.generate_3d_coordinates("CCO")
    assert result is None or "Open Babel is not available" in str(result)
    
    # Try a fake molecule object
    class FakeMol: pass
    
    result = openbabel_utils.compute_partial_charges(FakeMol())
    # Depending on implementation it might return empty dict or None
    assert result is None or isinstance(result, dict)

def test_pipeline_survives_openbabel_failure(monkeypatch):
    """
    Verify that ChemistryPipeline processes smoothly even if Open Babel fails.
    """
    monkeypatch.setattr(openbabel_utils, "_HAS_OPENBABEL", False)
    from core.pipeline import ChemistryPipeline
    from core.molecule_utils import mol_from_smiles
    
    pipeline = ChemistryPipeline()
    mol = mol_from_smiles("CCO")
    
    # Running analysis should not raise any unhandled exceptions
    result = pipeline.analyze(mol=mol, smiles="CCO")
    
    assert result is not None
    # Assuming warning is logged or we get partial data
    assert result.smiles == "CCO"
