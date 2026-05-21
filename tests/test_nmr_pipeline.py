
import pytest
from core.pipeline import ChemistryPipeline
from rdkit import Chem

def test_pipeline_nmr():
    pipeline = ChemistryPipeline()
    result = pipeline.analyze(smiles='c1ccccc1')
    assert result.proton_nmr_prediction is not None
    assert len(result.proton_nmr_prediction.signals) > 0
    assert result.proton_nmr_prediction.signals[0].ppm_mid > 0

    assert result.carbon_nmr_prediction is not None
    assert len(result.carbon_nmr_prediction.environments) > 0
    assert result.carbon_nmr_prediction.environments[0].ppm_range is not None
