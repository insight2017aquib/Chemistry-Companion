"""
services/batch_service.py
========================
Service layer for batch processing operations.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.pipeline import ChemistryPipeline
from exports.exporters import CsvExporter, ExcelExporter, JsonExporter
from exports.schemas.batch_export_schema import build_batch_export_payload

logger = logging.getLogger(__name__)


class BatchService:
    """Service for handling batch molecule analysis operations."""

    def __init__(self, max_workers: int = 4):
        self.pipeline = ChemistryPipeline(include_spectra=True)
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.csv_exporter = CsvExporter()
        self.json_exporter = JsonExporter()
        self.excel_exporter = ExcelExporter()

    def process_batch(
        self,
        molecules: List[Dict[str, str]],
        include_spectra: bool = True,
        save_images: bool = False,
        export_formats: Optional[List[str]] = None,
        output_dir: Optional[str] = None,
        progress_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        Process a batch of molecules.

        Args:
            molecules: List of molecule inputs
            include_spectra: Include spectral predictions
            save_images: Generate 2D structure images
            export_formats: Export formats to generate
            output_dir: Output directory path
            progress_callback: Optional progress callback function

        Returns:
            Batch processing results
        """
        total_molecules = len(molecules)
        results = []
        successful = 0
        failed = 0

        # Set output directory
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
        else:
            output_path = Path("output/batch")
            output_path.mkdir(parents=True, exist_ok=True)

        # Process molecules
        for i, mol_input in enumerate(molecules):
            try:
                # Update progress
                if progress_callback:
                    progress_callback(i + 1, total_molecules, mol_input.get("name", f"Molecule {i+1}"))

                # Analyze molecule
                result = self._analyze_single_molecule(
                    mol_input,
                    include_spectra,
                    save_images,
                    output_path
                )

                if result.get("success"):
                    successful += 1
                else:
                    failed += 1

                results.append(result)

            except Exception as e:
                logger.error(f"Failed to process molecule {i+1}: {e}")
                failed += 1
                results.append({
                    "input": mol_input,
                    "success": False,
                    "error": str(e)
                })

        # Generate exports if requested
        export_paths = {}
        if export_formats:
            export_paths = self._generate_exports(results, export_formats, output_path)

        # Create summary
        summary = {
            "total": total_molecules,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total_molecules if total_molecules > 0 else 0
        }

        return {
            "total_molecules": total_molecules,
            "successful_analyses": successful,
            "failed_analyses": failed,
            "results": results,
            "export_paths": export_paths,
            "summary": summary,
            "warnings": [],
            "errors": []
        }

    def _analyze_single_molecule(
        self,
        mol_input: Dict[str, str],
        include_spectra: bool,
        save_images: bool,
        output_path: Path
    ) -> Dict[str, Any]:
        """Analyze a single molecule."""
        try:
            # Extract input parameters
            smiles = mol_input.get("smiles")
            inchi = mol_input.get("inchi")
            iupac = mol_input.get("iupac")
            name = mol_input.get("name")

            # Set image path if saving images
            image_path = None
            if save_images and name:
                image_path = str(output_path / f"{name}.png")

            # Run analysis
            result = self.pipeline.analyze(
                smiles=smiles,
                inchi=inchi,
                iupac=iupac,
                name=name,
                save_image=save_images,
                image_path=image_path,
            )

            # Convert to dict format
            if result.metadata.get("error") or result.molecule is None:
                return {
                    "input": mol_input,
                    "success": False,
                    "error": result.metadata.get("error", "Analysis failed"),
                }
            formula = result.molecule.formula or (
                result.descriptors.formula if result.descriptors else None
            )
            return {
                "input": mol_input,
                "success": True,
                "molecule": {
                    "formula": formula,
                    "name": name or result.molecule.name,
                    "smiles": smiles or result.molecule.smiles,
                },
                "descriptors": result.descriptors,
                "functional_groups": result.functional_groups,
                "ir_prediction": result.ir_prediction,
                "proton_nmr_prediction": result.proton_nmr_prediction,
                "carbon_nmr_prediction": result.carbon_nmr_prediction,
                "visualization_path": result.visualization_path,
                "metadata": result.metadata,
            }

        except Exception as e:
            logger.error(f"Analysis failed for {mol_input}: {e}")
            return {
                "input": mol_input,
                "success": False,
                "error": str(e)
            }

    def _generate_exports(
        self,
        results: List[Dict[str, Any]],
        formats: List[str],
        output_path: Path
    ) -> Dict[str, str]:
        """Generate export files."""
        export_paths = {}

        try:
            payload = build_batch_export_payload(
                results,
                metadata={"export_context": "batch_service"},
            )

            for fmt in formats:
                normalized = fmt.lower()
                if normalized == "csv":
                    csv_path = self.csv_exporter.export(payload, output_path / "batch_results.csv")
                    export_paths["csv"] = str(csv_path)

                elif normalized == "json":
                    json_path = self.json_exporter.export(payload, output_path / "batch_results.json")
                    export_paths["json"] = str(json_path)

                elif normalized in {"xlsx", "excel"}:
                    xlsx_path = self.excel_exporter.export(payload, output_path / "batch_results.xlsx")
                    export_paths["xlsx"] = str(xlsx_path)

        except Exception as e:
            logger.error(f"Export generation failed: {e}")

        return export_paths

    def convert_batch_file(
        self,
        input_path: str,
        output_format: str,
        output_dir: Optional[str] = None,
        input_format: Optional[str] = None,
    ) -> str:
        """Convert a batch molecule file to a different structure format."""
        from core.batch_processor import convert_file_format

        return convert_file_format(
            input_path=input_path,
            output_format=output_format,
            output_dir=output_dir,
            input_format=input_format,
        )

    def _export_csv(self, results: List[Dict[str, Any]], path: Path):
        """Backward-compatible CSV export wrapper."""
        self.csv_exporter.export(build_batch_export_payload(results), path)

    def _export_json(self, results: List[Dict[str, Any]], path: Path):
        """Backward-compatible JSON export wrapper."""
        self.json_exporter.export(build_batch_export_payload(results), path)
