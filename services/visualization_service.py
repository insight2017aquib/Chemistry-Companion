"""
services/visualization_service.py
=================================
Service layer for visualization logic.
Checks HAS_VISUALIZATION before calling any rendering code.
"""

import logging
from visualization import HAS_VISUALIZATION

logger = logging.getLogger(__name__)

# Message shown when the visualization stack is not installed
_UNAVAILABLE_MSG = (
    "Visualization features require additional dependencies (gemmi, rdkit, py3Dmol). "
    "Install them with: pip install gemmi rdkit py3Dmol"
)


class VisualizationService:
    """API-friendly facade for the visualization package."""

    @staticmethod
    def is_available() -> bool:
        """Check whether the visualization backend is ready."""
        return HAS_VISUALIZATION

    @staticmethod
    def unavailable_message() -> str:
        import visualization
        err = getattr(visualization, "_import_error", "")
        if err:
            return (
                f"Visualization features require additional dependencies.\n"
                f"Detail: {err}\n"
                f"Please run: pip install gemmi rdkit py3Dmol"
            )
        return _UNAVAILABLE_MSG

    @staticmethod
    def process_protein(pdb_text: str, filename: str = "protein"):
        if not HAS_VISUALIZATION:
            raise RuntimeError(_UNAVAILABLE_MSG)
        from visualization import VisualizationOrchestrator
        return VisualizationOrchestrator.process_protein(pdb_text, filename)

    @staticmethod
    def process_ligand(smiles: str):
        if not HAS_VISUALIZATION:
            raise RuntimeError(_UNAVAILABLE_MSG)
        from visualization import VisualizationOrchestrator
        return VisualizationOrchestrator.process_ligand(smiles)

    @staticmethod
    def render_complex(
        protein_pdb: str,
        ligand_structure: str,
        protein_format: str = "pdb",
        ligand_format: str = "pdbqt",
    ):
        if not HAS_VISUALIZATION:
            raise RuntimeError(_UNAVAILABLE_MSG)
        from visualization import VisualizationOrchestrator
        return VisualizationOrchestrator.render_complex(
            protein_pdb,
            ligand_structure,
            protein_format=protein_format,
            ligand_format=ligand_format,
        )
