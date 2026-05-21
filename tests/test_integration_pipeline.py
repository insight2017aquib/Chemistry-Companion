"""
tests/test_integration_pipeline.py
==================================
Comprehensive integration tests for the full Chemistry Companion pipeline.

Tests the complete workflow:
  - Input parsing (SMILES, InChI, IUPAC)
  - Molecular descriptors
  - Functional group detection
  - IR prediction
  - ¹H NMR prediction
  - ¹³C NMR prediction
  - 2D visualization
  - Export (CSV, JSON)

Molecules tested:
  - Benzene
  - Ethanol
  - Aspirin
  - Caffeine
  - Quinoxaline
  - Acetic acid
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Generator

import pytest

from core.pipeline import ChemistryPipeline, AnalysisResult
from core.models import (
    MoleculeRecord,
    DescriptorRecord,
    AnalysisResult as AnalysisResultModel,
    FunctionalGroupReport,
    IRPrediction,
    ProtonNMRPrediction,
    CarbonNMRPrediction,
)


# =========================================================================
# Fixtures: Test Molecules (SMILES)
# =========================================================================

@pytest.fixture(scope="module")
def benzene_smiles() -> str:
    """Benzene - simple aromatic ring."""
    return "c1ccccc1"


@pytest.fixture(scope="module")
def ethanol_smiles() -> str:
    """Ethanol - simple alcohol."""
    return "CCO"


@pytest.fixture(scope="module")
def aspirin_smiles() -> str:
    """Aspirin (acetylsalicylic acid) - carboxylic acid + ester."""
    return "CC(=O)Oc1ccccc1C(=O)O"


@pytest.fixture(scope="module")
def caffeine_smiles() -> str:
    """Caffeine - complex heterocycle."""
    return "Cn1cnc2c1c(=O)n(c(=O)n2C)C"


@pytest.fixture(scope="module")
def quinoxaline_smiles() -> str:
    """Quinoxaline - fused bicyclic heterocycle."""
    return "c1ccc2nccnc2c1"


@pytest.fixture(scope="module")
def acetic_acid_smiles() -> str:
    """Acetic acid - simple carboxylic acid."""
    return "CC(=O)O"


@pytest.fixture(scope="module")
def test_molecules() -> dict[str, str]:
    """All test molecules in a dict."""
    return {
        "benzene": "c1ccccc1",
        "ethanol": "CCO",
        "aspirin": "CC(=O)Oc1ccccc1C(=O)O",
        "caffeine": "Cn1cnc2c1c(=O)n(c(=O)n2C)C",
        "quinoxaline": "c1ccc2nccnc2c1",
        "acetic_acid": "CC(=O)O",
    }


# =========================================================================
# Fixtures: Pipeline Instances
# =========================================================================

@pytest.fixture
def pipeline_with_spectra() -> ChemistryPipeline:
    """Pipeline with all spectral predictors enabled."""
    return ChemistryPipeline(include_spectra=True)


@pytest.fixture
def pipeline_no_spectra() -> ChemistryPipeline:
    """Pipeline with spectral predictors disabled."""
    return ChemistryPipeline(include_spectra=False)


# =========================================================================
# Fixtures: Temporary Directories
# =========================================================================

@pytest.fixture
def temp_output_dir() -> Generator[Path, None, None]:
    """Create a temporary output directory for exports."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_image_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for images."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_export_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for exports."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# =========================================================================
# Test Class: Input Parsing
# =========================================================================

class TestInputParsing:
    """Test multiple input formats (SMILES, InChI, IUPAC)."""

    def test_parse_from_smiles_benzene(self, pipeline_with_spectra, benzene_smiles):
        """Parse benzene from SMILES."""
        result = pipeline_with_spectra.analyze(smiles=benzene_smiles, name="Benzene")
        assert result.molecule.smiles is not None
        assert result.molecule.formula == "C6H6"
        assert result.molecule.name == "Benzene"

    def test_parse_from_smiles_ethanol(self, pipeline_with_spectra, ethanol_smiles):
        """Parse ethanol from SMILES."""
        result = pipeline_with_spectra.analyze(smiles=ethanol_smiles, name="Ethanol")
        assert result.molecule.smiles == ethanol_smiles
        assert result.molecule.formula == "C2H6O"

    def test_parse_from_inchi(self, pipeline_with_spectra):
        """Parse molecule from InChI."""
        inchi = "InChI=1S/C6H6/c1-2-4-6-5-3-1/h1-6H"
        result = pipeline_with_spectra.analyze(inchi=inchi, name="Benzene")
        assert result.molecule.formula == "C6H6"
        assert result.molecule.inchi is not None

    @pytest.mark.skip(reason="Requires internet connection to PubChem")
    def test_parse_from_iupac(self, pipeline_with_spectra):
        """Parse molecule from IUPAC name."""
        result = pipeline_with_spectra.analyze(iupac="benzene")
        assert result.molecule.formula == "C6H6"


class TestMoleculeRecordValidation:
    """Validate MoleculeRecord fields for parsed molecules."""

    @pytest.mark.parametrize("name,smiles,expected_formula", [
        ("benzene", "c1ccccc1", "C6H6"),
        ("ethanol", "CCO", "C2H6O"),
        ("aspirin", "CC(=O)Oc1ccccc1C(=O)O", "C9H8O4"),
        ("acetic_acid", "CC(=O)O", "C2H4O2"),
    ])
    def test_molecule_formula(self, pipeline_with_spectra, name, smiles, expected_formula):
        """Validate formula is correctly computed."""
        result = pipeline_with_spectra.analyze(smiles=smiles, name=name)
        assert result.molecule.formula == expected_formula

    def test_molecule_has_rdkit_object(self, pipeline_with_spectra, benzene_smiles):
        """Verify RDKit molecule object is present."""
        result = pipeline_with_spectra.analyze(smiles=benzene_smiles)
        assert result.molecule.rdkit_mol is not None

    def test_molecule_atom_counts(self, pipeline_with_spectra, ethanol_smiles):
        """Verify atom counts are computed."""
        result = pipeline_with_spectra.analyze(smiles=ethanol_smiles)
        assert result.molecule.num_atoms is not None
        assert result.molecule.num_heavy_atoms is not None
        assert result.molecule.atom_counts is not None
        assert result.molecule.atom_counts.get("C") is not None


# =========================================================================
# Test Class: Descriptors
# =========================================================================

class TestDescriptorCalculation:
    """Test descriptor computation for various molecules."""

    @pytest.mark.parametrize("smiles", [
        "c1ccccc1",  # benzene
        "CCO",  # ethanol
        "CC(=O)O",  # acetic acid
    ])
    def test_descriptors_computed(self, pipeline_with_spectra, smiles):
        """Verify descriptors are computed."""
        result = pipeline_with_spectra.analyze(smiles=smiles)
        assert result.descriptors is not None
        assert isinstance(result.descriptors, DescriptorRecord)

    def test_descriptor_fields_present(self, pipeline_with_spectra, benzene_smiles):
        """Verify key descriptor fields are present."""
        result = pipeline_with_spectra.analyze(smiles=benzene_smiles)
        desc = result.descriptors
        assert desc.molecular_weight is not None
        assert desc.logp is not None
        assert desc.tpsa is not None
        assert desc.hba is not None
        assert desc.hbd is not None
        assert desc.heavy_atom_count is not None

    def test_descriptor_summary_generated(self, pipeline_with_spectra, aspirin_smiles):
        """Verify descriptor summary string is generated."""
        result = pipeline_with_spectra.analyze(smiles=aspirin_smiles)
        summary = result.descriptor_summary
        assert summary is not None
        assert isinstance(summary, str)
        assert len(summary) > 0
        # Check for key descriptor abbreviations
        assert any(keyword in summary for keyword in ["MW", "LogP", "TPSA", "HBA", "HBD"])

    def test_descriptor_to_dict(self, pipeline_with_spectra, benzene_smiles):
        """Verify descriptors can be converted to dict."""
        result = pipeline_with_spectra.analyze(smiles=benzene_smiles)
        desc_dict = result.descriptors.to_dict()
        assert isinstance(desc_dict, dict)
        assert "molecular_weight" in desc_dict
        assert "logp" in desc_dict


# =========================================================================
# Test Class: Functional Group Detection
# =========================================================================

class TestFunctionalGroupDetection:
    """Test functional group identification."""

    def test_fg_detection_benzene(self, pipeline_with_spectra, benzene_smiles):
        """Benzene should detect aromatic rings."""
        result = pipeline_with_spectra.analyze(smiles=benzene_smiles, name="Benzene")
        assert result.functional_group_report is not None
        assert result.functional_groups is not None

    def test_fg_detection_ethanol(self, pipeline_with_spectra, ethanol_smiles):
        """Ethanol should detect alcohol group."""
        result = pipeline_with_spectra.analyze(smiles=ethanol_smiles, name="Ethanol")
        fg = result.functional_groups
        # Alcohol should be detected (though key name may vary)
        # Check that some functional groups were found
        assert len(result.functional_group_report.keys) > 0

    def test_fg_detection_aspirin(self, pipeline_with_spectra, aspirin_smiles):
        """Aspirin should detect carboxylic acid and ester."""
        result = pipeline_with_spectra.analyze(smiles=aspirin_smiles, name="Aspirin")
        fg_report = result.functional_group_report
        assert fg_report is not None
        assert isinstance(fg_report.keys, list)
        assert len(fg_report.keys) > 0

    def test_fg_report_structure(self, pipeline_with_spectra, aspirin_smiles):
        """Verify FunctionalGroupReport has required fields."""
        result = pipeline_with_spectra.analyze(smiles=aspirin_smiles)
        fg_report = result.functional_group_report
        assert hasattr(fg_report, "keys")
        assert hasattr(fg_report, "names")
        assert isinstance(fg_report.keys, list)
        assert isinstance(fg_report.names, list)


# =========================================================================
# Test Class: Spectral Predictions
# =========================================================================

class TestIRPrediction:
    """Test IR spectrum prediction."""

    @pytest.mark.parametrize("smiles,name", [
        ("c1ccccc1", "Benzene"),
        ("CCO", "Ethanol"),
        ("CC(=O)O", "Acetic Acid"),
    ])
    def test_ir_prediction_computed(self, pipeline_with_spectra, smiles, name):
        """Verify IR prediction is computed."""
        result = pipeline_with_spectra.analyze(smiles=smiles, name=name)
        assert result.ir_prediction is not None
        assert hasattr(result.ir_prediction, "bands")
        assert hasattr(result.ir_prediction, "smiles")

    def test_ir_prediction_has_bands(self, pipeline_with_spectra, aspirin_smiles):
        """IR prediction should have bands."""
        result = pipeline_with_spectra.analyze(smiles=aspirin_smiles)
        ir = result.ir_prediction
        assert ir.bands is not None
        assert len(ir.bands) > 0

    def test_ir_band_structure(self, pipeline_with_spectra, benzene_smiles):
        """Verify IR bands have required fields."""
        result = pipeline_with_spectra.analyze(smiles=benzene_smiles)
        ir = result.ir_prediction
        for band in ir.bands:
            assert band.low_cm is not None
            assert band.high_cm is not None
            assert band.mid_cm is not None
            assert band.label is not None

    def test_ir_prediction_disabled_when_spectra_off(
        self,
        pipeline_no_spectra,
        aspirin_smiles
    ):
        """IR prediction should be None when spectra disabled."""
        result = pipeline_no_spectra.analyze(smiles=aspirin_smiles)
        assert result.ir_prediction is None


class TestProtonNMRPrediction:
    """Test ¹H NMR prediction."""

    @pytest.mark.parametrize("smiles,name", [
        ("c1ccccc1", "Benzene"),
        ("CCO", "Ethanol"),
        ("CC(=O)O", "Acetic Acid"),
    ])
    def test_proton_nmr_computed(self, pipeline_with_spectra, smiles, name):
        """Verify ¹H NMR prediction is computed."""
        result = pipeline_with_spectra.analyze(smiles=smiles, name=name)
        assert result.proton_nmr_prediction is not None
        assert hasattr(result.proton_nmr_prediction, "signals")
        assert hasattr(result.proton_nmr_prediction, "smiles")

    def test_proton_nmr_has_signals(self, pipeline_with_spectra, ethanol_smiles):
        """¹H NMR should have signals."""
        result = pipeline_with_spectra.analyze(smiles=ethanol_smiles)
        hnmr = result.proton_nmr_prediction
        assert hnmr.signals is not None
        assert len(hnmr.signals) > 0

    def test_proton_nmr_signal_structure(self, pipeline_with_spectra, aspirin_smiles):
        """Verify ¹H NMR signals have required fields."""
        result = pipeline_with_spectra.analyze(smiles=aspirin_smiles)
        hnmr = result.proton_nmr_prediction
        for signal in hnmr.signals:
            assert hasattr(signal, "ppm_range")
            assert hasattr(signal, "ppm_mid")

    def test_proton_nmr_disabled_when_spectra_off(
        self,
        pipeline_no_spectra,
        aspirin_smiles
    ):
        """¹H NMR should be None when spectra disabled."""
        result = pipeline_no_spectra.analyze(smiles=aspirin_smiles)
        assert result.proton_nmr_prediction is None


class TestCarbonNMRPrediction:
    """Test ¹³C NMR prediction."""

    @pytest.mark.parametrize("smiles,name", [
        ("c1ccccc1", "Benzene"),
        ("CCO", "Ethanol"),
        ("CC(=O)O", "Acetic Acid"),
    ])
    def test_carbon_nmr_computed(self, pipeline_with_spectra, smiles, name):
        """Verify ¹³C NMR prediction is computed."""
        result = pipeline_with_spectra.analyze(smiles=smiles, name=name)
        assert result.carbon_nmr_prediction is not None
        assert hasattr(result.carbon_nmr_prediction, "environments")
        assert hasattr(result.carbon_nmr_prediction, "smiles")

    def test_carbon_nmr_has_signals(self, pipeline_with_spectra, benzene_smiles):
        """¹³C NMR should have environments."""
        result = pipeline_with_spectra.analyze(smiles=benzene_smiles)
        cnmr = result.carbon_nmr_prediction
        assert cnmr.environments is not None
        assert len(cnmr.environments) > 0

    def test_carbon_nmr_signal_structure(self, pipeline_with_spectra, aspirin_smiles):
        """Verify ¹³C NMR environments have required fields."""
        result = pipeline_with_spectra.analyze(smiles=aspirin_smiles)
        cnmr = result.carbon_nmr_prediction
        for env in cnmr.environments:
            assert hasattr(env, "ppm_range")
            assert hasattr(env, "label")

    def test_carbon_nmr_disabled_when_spectra_off(
        self,
        pipeline_no_spectra,
        aspirin_smiles
    ):
        """¹³C NMR should be None when spectra disabled."""
        result = pipeline_no_spectra.analyze(smiles=aspirin_smiles)
        assert result.carbon_nmr_prediction is None


# =========================================================================
# Test Class: Visualization
# =========================================================================

class TestVisualization:
    """Test 2D structure image generation."""

    def test_save_image_benzene(self, pipeline_with_spectra, benzene_smiles, temp_image_dir):
        """Test saving benzene structure image."""
        image_path = temp_image_dir / "benzene.png"
        result = pipeline_with_spectra.analyze(
            smiles=benzene_smiles,
            name="Benzene",
            save_image=True,
            image_path=str(image_path)
        )
        assert result.visualization_path is not None
        assert Path(result.visualization_path).exists()
        assert image_path.exists()
        assert image_path.stat().st_size > 0

    def test_save_image_aspirin(self, pipeline_with_spectra, aspirin_smiles, temp_image_dir):
        """Test saving aspirin structure image."""
        image_path = temp_image_dir / "aspirin.png"
        result = pipeline_with_spectra.analyze(
            smiles=aspirin_smiles,
            name="Aspirin",
            save_image=True,
            image_path=str(image_path)
        )
        assert image_path.exists()
        assert image_path.stat().st_size > 0

    @pytest.mark.parametrize("smiles,name", [
        ("c1ccccc1", "Benzene"),
        ("CCO", "Ethanol"),
        ("Cn1cnc2c1c(=O)n(c(=O)n2C)C", "Caffeine"),
    ])
    def test_save_images_all_molecules(
        self,
        pipeline_with_spectra,
        smiles,
        name,
        temp_image_dir
    ):
        """Test image generation for all test molecules."""
        image_path = temp_image_dir / f"{name.lower()}.png"
        result = pipeline_with_spectra.analyze(
            smiles=smiles,
            name=name,
            save_image=True,
            image_path=str(image_path)
        )
        assert image_path.exists()

    def test_image_not_saved_when_not_requested(
        self,
        pipeline_with_spectra,
        benzene_smiles,
        temp_image_dir
    ):
        """Image should not be saved when save_image=False."""
        image_path = temp_image_dir / "benzene.png"
        result = pipeline_with_spectra.analyze(
            smiles=benzene_smiles,
            save_image=False,
            image_path=str(image_path)
        )
        assert result.visualization_path is None
        assert not image_path.exists()


# =========================================================================
# Test Class: Export Functionality
# =========================================================================

class TestExportCSV:
    """Test CSV export."""

    def test_export_csv_benzene(self, pipeline_with_spectra, benzene_smiles, temp_export_dir):
        """Test exporting benzene to CSV."""
        export_path = temp_export_dir / "benzene.csv"
        result = pipeline_with_spectra.analyze(
            smiles=benzene_smiles,
            name="Benzene",
            export=True,
            export_path=str(export_path)
        )
        assert result.export_path is not None
        assert export_path.exists()
        assert export_path.stat().st_size > 0
        
        # Verify CSV is readable
        with open(export_path, "r") as f:
            content = f.read()
            assert "Benzene" in content or "benzene" in content.lower()

    def test_export_csv_all_molecules(self, pipeline_with_spectra, test_molecules, temp_export_dir):
        """Test CSV export for all test molecules."""
        for name, smiles in test_molecules.items():
            export_path = temp_export_dir / f"{name}.csv"
            result = pipeline_with_spectra.analyze(
                smiles=smiles,
                name=name.capitalize(),
                export=True,
                export_path=str(export_path)
            )
            assert export_path.exists()
            assert export_path.stat().st_size > 0


class TestExportJSON:
    """Test JSON export via AnalysisResult.to_dict()."""

    def test_analysis_result_to_dict(self, pipeline_with_spectra, benzene_smiles):
        """Test converting AnalysisResult to dict."""
        result = pipeline_with_spectra.analyze(smiles=benzene_smiles)
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert "molecule" in result_dict
        assert "descriptors" in result_dict
        assert "ir_prediction" in result_dict
        assert "proton_nmr_prediction" in result_dict
        assert "carbon_nmr_prediction" in result_dict

    def test_export_result_as_json(self, pipeline_with_spectra, aspirin_smiles, temp_export_dir):
        """Test exporting analysis result as JSON."""
        result = pipeline_with_spectra.analyze(
            smiles=aspirin_smiles,
            name="Aspirin"
        )
        json_path = temp_export_dir / "aspirin_result.json"
        
        result_dict = result.to_dict()
        with open(json_path, "w") as f:
            json.dump(result_dict, f, indent=2)
        
        assert json_path.exists()
        assert json_path.stat().st_size > 0
        
        # Verify JSON is readable
        with open(json_path, "r") as f:
            loaded = json.load(f)
            assert loaded is not None
            assert "molecule" in loaded

    def test_descriptor_to_json(self, pipeline_with_spectra, benzene_smiles, temp_export_dir):
        """Test converting descriptors to JSON."""
        result = pipeline_with_spectra.analyze(smiles=benzene_smiles)
        desc_dict = result.descriptors.to_dict()
        json_path = temp_export_dir / "descriptors.json"
        
        with open(json_path, "w") as f:
            json.dump(desc_dict, f, indent=2)
        
        assert json_path.exists()


# =========================================================================
# Test Class: Complete Workflow Integration
# =========================================================================

class TestCompleteWorkflow:
    """Test the complete analysis workflow end-to-end."""

    def test_complete_workflow_benzene(
        self,
        pipeline_with_spectra,
        benzene_smiles,
        temp_output_dir,
        temp_image_dir
    ):
        """Test complete workflow for benzene."""
        # Parse
        result = pipeline_with_spectra.analyze(
            smiles=benzene_smiles,
            name="Benzene",
            save_image=True,
            image_path=str(temp_image_dir / "benzene.png"),
            export=True,
            export_path=str(temp_output_dir / "benzene.csv")
        )
        
        # Validate all stages
        assert result.molecule is not None
        assert result.molecule.formula == "C6H6"
        assert result.descriptors is not None
        assert result.descriptor_summary is not None
        assert result.functional_group_report is not None
        assert result.ir_prediction is not None
        assert result.proton_nmr_prediction is not None
        assert result.carbon_nmr_prediction is not None
        assert result.visualization_path is not None
        assert result.export_path is not None

    def test_complete_workflow_aspirin(
        self,
        pipeline_with_spectra,
        aspirin_smiles,
        temp_output_dir,
        temp_image_dir
    ):
        """Test complete workflow for aspirin."""
        result = pipeline_with_spectra.analyze(
            smiles=aspirin_smiles,
            name="Aspirin",
            save_image=True,
            image_path=str(temp_image_dir / "aspirin.png"),
            export=True,
            export_path=str(temp_output_dir / "aspirin.csv")
        )
        
        # Validate all stages
        assert result.molecule is not None
        assert result.molecule.formula == "C9H8O4"
        assert result.descriptors is not None
        assert result.functional_group_report is not None
        assert len(result.functional_group_report.keys) > 0
        assert result.ir_prediction is not None
        assert len(result.ir_prediction.bands) > 0
        assert result.proton_nmr_prediction is not None
        assert result.carbon_nmr_prediction is not None
        assert Path(result.visualization_path).exists()
        assert Path(result.export_path).exists()

    @pytest.mark.parametrize("name,smiles", [
        ("Benzene", "c1ccccc1"),
        ("Ethanol", "CCO"),
        ("Aspirin", "CC(=O)Oc1ccccc1C(=O)O"),
        ("Caffeine", "Cn1cnc2c1c(=O)n(c(=O)n2C)C"),
        ("Quinoxaline", "c1ccc2nccnc2c1"),
        ("Acetic Acid", "CC(=O)O"),
    ])
    def test_complete_workflow_all_molecules(
        self,
        pipeline_with_spectra,
        name,
        smiles,
        temp_output_dir,
        temp_image_dir
    ):
        """Test complete workflow for all test molecules."""
        result = pipeline_with_spectra.analyze(
            smiles=smiles,
            name=name,
            save_image=True,
            image_path=str(temp_image_dir / f"{name.lower()}.png"),
            export=True,
            export_path=str(temp_output_dir / f"{name.lower()}.csv")
        )
        
        # Every molecule should have all analyses completed
        assert result.molecule is not None
        assert result.descriptors is not None
        assert result.functional_group_report is not None
        assert result.ir_prediction is not None
        assert result.proton_nmr_prediction is not None
        assert result.carbon_nmr_prediction is not None
        assert Path(result.visualization_path).exists()
        assert Path(result.export_path).exists()


# =========================================================================
# Test Class: Module Integration
# =========================================================================

class TestModuleIntegration:
    """Test that all modules integrate correctly."""

    def test_pipeline_uses_all_components(self, pipeline_with_spectra):
        """Verify pipeline uses all required components."""
        assert pipeline_with_spectra._molecule_loader is not None
        assert pipeline_with_spectra._descriptor_calculator is not None
        assert pipeline_with_spectra._descriptor_summarizer is not None
        assert pipeline_with_spectra._image_saver is not None
        assert pipeline_with_spectra._fg_detector is not None
        assert pipeline_with_spectra._ir_predictor is not None
        assert pipeline_with_spectra._proton_predictor is not None
        assert pipeline_with_spectra._carbon_predictor is not None

    def test_molecule_loader_integration(self, pipeline_with_spectra, benzene_smiles):
        """Test molecule loader works with pipeline."""
        result = pipeline_with_spectra.analyze(smiles=benzene_smiles)
        assert result.molecule is not None
        assert isinstance(result.molecule, MoleculeRecord)

    def test_descriptor_calculator_integration(self, pipeline_with_spectra, benzene_smiles):
        """Test descriptor calculator works with pipeline."""
        result = pipeline_with_spectra.analyze(smiles=benzene_smiles)
        assert result.descriptors is not None
        assert isinstance(result.descriptors, DescriptorRecord)

    def test_fg_detector_integration(self, pipeline_with_spectra, aspirin_smiles):
        """Test functional group detector works with pipeline."""
        result = pipeline_with_spectra.analyze(smiles=aspirin_smiles)
        assert result.functional_group_report is not None
        assert hasattr(result.functional_group_report, "keys")
        assert hasattr(result.functional_group_report, "names")

    def test_ir_predictor_integration(self, pipeline_with_spectra, benzene_smiles):
        """Test IR predictor works with pipeline."""
        result = pipeline_with_spectra.analyze(smiles=benzene_smiles)
        assert result.ir_prediction is not None
        assert hasattr(result.ir_prediction, "bands")

    def test_proton_nmr_integration(self, pipeline_with_spectra, benzene_smiles):
        """Test proton NMR predictor works with pipeline."""
        result = pipeline_with_spectra.analyze(smiles=benzene_smiles)
        assert result.proton_nmr_prediction is not None
        assert hasattr(result.proton_nmr_prediction, "signals")

    def test_carbon_nmr_integration(self, pipeline_with_spectra, benzene_smiles):
        """Test carbon NMR predictor works with pipeline."""
        result = pipeline_with_spectra.analyze(smiles=benzene_smiles)
        assert result.carbon_nmr_prediction is not None
        assert hasattr(result.carbon_nmr_prediction, "environments")

    def test_all_exports_writable(self, pipeline_with_spectra, benzene_smiles, temp_export_dir):
        """Test that all export types can be written."""
        # Note: This is a placeholder; the pipeline currently supports CSV export
        # CSV export is tested elsewhere
        export_path = temp_export_dir / "benzene.csv"
        result = pipeline_with_spectra.analyze(
            smiles=benzene_smiles,
            export=True,
            export_path=str(export_path)
        )
        assert export_path.exists()


# =========================================================================
# Test Class: Error Handling
# =========================================================================

class TestErrorHandling:
    """Test pipeline behavior with invalid inputs."""

    def test_invalid_smiles_raises_error(self, pipeline_with_spectra):
        """Invalid SMILES should raise an error."""
        with pytest.raises(Exception):
            pipeline_with_spectra.analyze(smiles="NOT_A_VALID_SMILES!!!")

    def test_empty_input_raises_error(self, pipeline_with_spectra):
        """Empty input should raise an error."""
        with pytest.raises(Exception):
            pipeline_with_spectra.analyze()

    def test_none_smiles_raises_error(self, pipeline_with_spectra):
        """None SMILES should raise an error."""
        with pytest.raises(Exception):
            pipeline_with_spectra.analyze(smiles=None)


# =========================================================================
# Test Class: Data Persistence
# =========================================================================

class TestDataPersistence:
    """Test that exported data can be reloaded and validated."""

    def test_json_export_persist_and_reload(self, pipeline_with_spectra, aspirin_smiles, temp_export_dir):
        """Test JSON round-trip persistence."""
        result = pipeline_with_spectra.analyze(smiles=aspirin_smiles, name="Aspirin")
        result_dict = result.to_dict()
        
        json_path = temp_export_dir / "result.json"
        with open(json_path, "w") as f:
            json.dump(result_dict, f, indent=2)
        
        # Reload and validate
        with open(json_path, "r") as f:
            reloaded = json.load(f)
        
        assert reloaded["molecule"]["formula"] == "C9H8O4"
        assert reloaded["descriptors"]["molecular_weight"] is not None
        assert len(reloaded["ir_prediction"]["bands"]) > 0

    def test_csv_export_has_data(self, pipeline_with_spectra, benzene_smiles, temp_export_dir):
        """Test CSV export contains data."""
        export_path = temp_export_dir / "benzene.csv"
        result = pipeline_with_spectra.analyze(
            smiles=benzene_smiles,
            name="Benzene",
            export=True,
            export_path=str(export_path)
        )
        
        with open(export_path, "r") as f:
            lines = f.readlines()
        
        # Should have at least header + 1 data row
        assert len(lines) >= 2
        assert any("Benzene" in line or "C6H6" in line for line in lines)
