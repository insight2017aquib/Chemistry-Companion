"""
tests/test_pipeline.py
=======================
Pytest suite for core/pipeline.py (ChemistryPipeline)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from core.pipeline import ChemistryPipeline, AnalysisResult
from core.molecule_utils import load_molecule


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def benzene_smiles() -> str:
    return "c1ccccc1"


@pytest.fixture(scope="session")
def aspirin_smiles() -> str:
    return "CC(=O)Oc1ccccc1C(=O)O"


@pytest.fixture(scope="session")
def caffeine_smiles() -> str:
    return "Cn1cnc2c1c(=O)n(c(=O)n2C)C"


@pytest.fixture
def pipeline() -> ChemistryPipeline:
    return ChemistryPipeline(include_spectra=True)


@pytest.fixture
def pipeline_no_spectra() -> ChemistryPipeline:
    return ChemistryPipeline(include_spectra=False)


# ---------------------------------------------------------------------------
# Basic Functionality Tests
# ---------------------------------------------------------------------------

class TestBasicAnalysis:
    def test_analyze_with_smiles(self, pipeline, benzene_smiles):
        result = pipeline.analyze(smiles=benzene_smiles, name="Benzene")
        assert isinstance(result, AnalysisResult)
        assert result.molecule.formula == "C6H6"
        assert result.descriptors is not None
        assert result.descriptor_summary is not None

    def test_analyze_with_name(self, pipeline, aspirin_smiles):
        result = pipeline.analyze(smiles=aspirin_smiles, name="Aspirin")
        assert result.molecule.name == "Aspirin"

    def test_run_alias(self, pipeline, benzene_smiles):
        result = pipeline.run(smiles=benzene_smiles)
        assert isinstance(result, AnalysisResult)


class TestInputMethods:
    def test_smiles_input(self, pipeline, benzene_smiles):
        result = pipeline.analyze(smiles=benzene_smiles)
        assert result.molecule.formula == "C6H6"

    def test_inchi_input(self, pipeline):
        inchi = "InChI=1S/C6H6/c1-2-4-6-5-3-1/h1-6H"
        result = pipeline.analyze(inchi=inchi)
        assert result.molecule.formula == "C6H6"

    def test_iupac_input(self, pipeline):
        result = pipeline.analyze(iupac="benzene")
        assert result.molecule.formula == "C6H6"


# ---------------------------------------------------------------------------
# Descriptor & Functional Group Tests
# ---------------------------------------------------------------------------

class TestDescriptors:
    def test_descriptors_present(self, pipeline, aspirin_smiles):
        result = pipeline.analyze(smiles=aspirin_smiles)
        assert result.descriptors.logp is not None
        assert result.descriptors.tpsa is not None
        assert result.descriptors.ro5_pass is not None

    def test_descriptor_summary(self, pipeline, benzene_smiles):
        result = pipeline.analyze(smiles=benzene_smiles)
        assert "LogP" in result.descriptor_summary
        assert "TPSA" in result.descriptor_summary


class TestFunctionalGroups:
    def test_functional_groups_present(self, pipeline, aspirin_smiles):
        result = pipeline.analyze(smiles=aspirin_smiles)
        assert isinstance(result.functional_groups, dict)
        assert len(result.functional_groups) > 0


# ---------------------------------------------------------------------------
# Spectral Prediction Tests
# ---------------------------------------------------------------------------

class TestSpectralPredictions:
    def test_ir_prediction(self, pipeline, aspirin_smiles):
        result = pipeline.analyze(smiles=aspirin_smiles)
        assert result.ir_prediction is not None

    def test_proton_nmr_prediction(self, pipeline, aspirin_smiles):
        result = pipeline.analyze(smiles=aspirin_smiles)
        assert result.proton_nmr_prediction is not None

    def test_carbon_nmr_prediction(self, pipeline, aspirin_smiles):
        result = pipeline.analyze(smiles=aspirin_smiles)
        assert result.carbon_nmr_prediction is not None

    def test_no_spectra_when_disabled(self, pipeline_no_spectra, aspirin_smiles):
        result = pipeline_no_spectra.analyze(smiles=aspirin_smiles)
        assert result.ir_prediction is None
        assert result.proton_nmr_prediction is None
        assert result.carbon_nmr_prediction is None


# ---------------------------------------------------------------------------
# Visualization & Export Tests
# ---------------------------------------------------------------------------

class TestVisualizationAndExport:
    def test_save_image(self, pipeline, aspirin_smiles, tmp_path):
        image_path = tmp_path / "aspirin.png"
        result = pipeline.analyze(
            smiles=aspirin_smiles,
            save_image=True,
            image_path=str(image_path)
        )
        assert result.visualization_path is not None
        assert image_path.exists()

    def test_export(self, pipeline, benzene_smiles, tmp_path):
        export_path = tmp_path / "benzene_export.csv"
        result = pipeline.analyze(
            smiles=benzene_smiles,
            export=True,
            export_path=str(export_path)
        )
        assert result.export_path is not None
        assert export_path.exists()


# ---------------------------------------------------------------------------
# AnalysisResult Tests
# ---------------------------------------------------------------------------

class TestAnalysisResult:
    def test_to_dict(self, pipeline, benzene_smiles):
        result = pipeline.analyze(smiles=benzene_smiles)
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "molecule" in d
        assert "descriptors" in d
        assert "ir_prediction" in d

    def test_metadata(self, pipeline, caffeine_smiles):
        result = pipeline.analyze(smiles=caffeine_smiles, name="Caffeine")
        assert "input" in result.metadata
        assert result.metadata["input"]["name"] == "Caffeine"


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_invalid_smiles_raises(self, pipeline):
        with pytest.raises(Exception):
            pipeline.analyze(smiles="NOT_A_VALID_SMILES!!!")

    def test_empty_input_raises(self, pipeline):
        with pytest.raises(Exception):
            pipeline.analyze()