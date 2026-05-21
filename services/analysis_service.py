"""
services/analysis_service.py
===========================
Service layer for molecule analysis operations.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from core.pipeline import ChemistryPipeline
from core.models import AnalysisResult

logger = logging.getLogger(__name__)


class AnalysisService:
    """Service for handling molecule analysis operations."""

    def __init__(self):
        self.pipeline = ChemistryPipeline(include_spectra=True)

    def analyze_molecule(
        self,
        smiles: Optional[str] = None,
        inchi: Optional[str] = None,
        iupac: Optional[str] = None,
        name: Optional[str] = None,
        include_spectra: bool = True,
        save_image: bool = False,
        image_path: Optional[str] = None,
        export_formats: Optional[list[str]] = None,
    ) -> AnalysisResult:
        """
        Analyze a single molecule.

        Args:
            smiles: SMILES string
            inchi: InChI string
            iupac: IUPAC name
            name: Molecule name
            include_spectra: Whether to include spectral predictions
            save_image: Whether to save 2D structure image
            image_path: Path for image file
            export_formats: List of export formats

        Returns:
            AnalysisResult object
        """
        try:
            # Update pipeline settings
            self.pipeline.include_spectra = include_spectra

            # Run analysis
            result = self.pipeline.analyze(
                smiles=smiles,
                inchi=inchi,
                iupac=iupac,
                name=name,
                save_image=save_image,
                image_path=image_path,
            )

            # Handle exports if requested
            if export_formats:
                export_paths = {}
                for fmt in export_formats:
                    if fmt.lower() in ["csv", "json", "xlsx"]:
                        # Generate export path
                        base_name = name or "molecule"
                        export_path = f"{base_name}.{fmt}"
                        if image_path:
                            export_dir = Path(image_path).parent
                            export_path = str(export_dir / f"{base_name}.{fmt}")

                        # Export (simplified - would need to implement export logic)
                        export_paths[fmt] = export_path

                # Add export paths to result metadata
                result.metadata["export_paths"] = export_paths

            return result

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            # Return minimal error result
            error_result = AnalysisResult(
                molecule=None,
                descriptors=None,
                descriptor_summary="Analysis failed",
                functional_groups={},
                functional_group_report=None,
                ir_prediction=None,
                proton_nmr_prediction=None,
                carbon_nmr_prediction=None,
                visualization_path=None,
                export_row=None,
                export_path=None,
                metadata={"error": str(e)}
            )
            return error_result

    def get_example_molecules(self) -> Dict[str, Dict[str, str]]:
        """Get example molecules for quick selection."""
        return {
            "benzene": {
                "smiles": "c1ccccc1",
                "name": "Benzene",
                "description": "Simple aromatic hydrocarbon"
            },
            "caffeine": {
                "smiles": "Cn1cnc2c1c(=O)n(c(=O)n2C)C",
                "name": "Caffeine",
                "description": "Purine alkaloid"
            },
            "aspirin": {
                "smiles": "CC(=O)Oc1ccccc1C(=O)O",
                "name": "Aspirin",
                "description": "Acetylsalicylic acid"
            },
            "quinoxaline": {
                "smiles": "c1cc2c(cc1)ncc[nH]2",
                "name": "Quinoxaline",
                "description": "Fused heterocycle"
            },
            "ethanol": {
                "smiles": "CCO",
                "name": "Ethanol",
                "description": "Simple alcohol"
            },
            "acetic_acid": {
                "smiles": "CC(=O)O",
                "name": "Acetic Acid",
                "description": "Carboxylic acid"
            }
        }