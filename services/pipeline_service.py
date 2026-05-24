"""
services/pipeline_service.py
=============================
Clean adapter between the GUI and the core docking/visualization logic.
Uses lazy imports and checks HAS_* flags so the app never crashes
even when vina, meeko, py3Dmol, or the LLM API key are absent.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class PipelineService:
    """
    Orchestrator for the new docking + visualization features.
    core/pipeline.py is never imported or modified.
    """

    # ── Availability Checks ─────────────────────────────────────

    @staticmethod
    def docking_available() -> bool:
        from docking_workflow import HAS_DOCKING
        return HAS_DOCKING

    @staticmethod
    def visualization_available() -> bool:
        from visualization import HAS_VISUALIZATION
        return HAS_VISUALIZATION

    @staticmethod
    def llm_available() -> bool:
        from llm import HAS_LLM
        return HAS_LLM

    # ── Docking ─────────────────────────────────────────────────

    @staticmethod
    def run_docking(
        protein_pdbqt: str,
        ligand_pdbqt: str,
        center: Dict[str, float],
        size: Dict[str, float],
        exhaustiveness: int = 8
    ) -> Dict[str, Any]:
        """Run the full Vina pipeline.  Returns report dict or error dict."""
        if not PipelineService.docking_available():
            return {
                "status": "unavailable",
                "error": "Docking requires additional setup. Install: conda install -c conda-forge vina openbabel && pip install meeko"
            }

        try:
            from docking_workflow.vina_runner import run_vina
            from docking_workflow.pose_manager import parse_vina_output
            from docking_workflow.interaction_mapper import map_interactions
            from docking_workflow.report_builder import build_docking_report

            result = run_vina(
                protein_pdbqt=protein_pdbqt,
                ligand_pdbqt=ligand_pdbqt,
                center_x=center.get("x", 0.0),
                center_y=center.get("y", 0.0),
                center_z=center.get("z", 0.0),
                size_x=size.get("x", 20.0),
                size_y=size.get("y", 20.0),
                size_z=size.get("z", 20.0),
                exhaustiveness=exhaustiveness
            )

            poses = parse_vina_output(result.pdbqt_output)
            interactions = []
            if poses:
                interactions = map_interactions(protein_pdbqt, poses[0].pdbqt_block)

            return build_docking_report(poses, interactions)

        except ImportError as e:
            logger.error("Docking import failed: %s", e)
            return {"status": "unavailable", "error": f"Missing dependency: {e}"}
        except Exception as e:
            logger.error("Docking pipeline failed: %s", e)
            return {"status": "failed", "error": str(e)}

    # ── LLM Explanation ─────────────────────────────────────────

    @staticmethod
    def get_docking_explanation(
        poses: List[Dict[str, Any]],
        interactions: List[Dict[str, Any]],
        smiles: str
    ) -> str:
        """Generate an LLM explanation; returns fallback string on failure."""
        if not PipelineService.llm_available():
            return (
                "LLM integration is unavailable. "
                "Configure OPENROUTER_API_KEY in your .env file to enable AI explanations."
            )

        try:
            from llm.docking_explainer import explain_docking_result
            return explain_docking_result(poses, interactions, smiles)
        except ImportError as e:
            logger.error("LLM import failed: %s", e)
            return f"LLM unavailable (missing dependency: {e})"
        except Exception as e:
            logger.error("LLM explanation failed: %s", e)
            return f"Failed to generate explanation: {e}"

    # ── Visualization ───────────────────────────────────────────

    @staticmethod
    def generate_visualization(
        protein_pdb: str,
        ligand_pdbqt: str
    ) -> Dict[str, str]:
        """Generate a 3D overlay; returns error dict on failure."""
        if not PipelineService.visualization_available():
            import visualization
            err = getattr(visualization, "_import_error", "")
            detail = f" ({err})" if err else ""
            return {
                "status": "unavailable",
                "error": f"Visualization requires additional setup{detail}. Install: pip install gemmi rdkit py3Dmol"
            }

        try:
            from visualization.complex_renderer import render_protein_ligand_complex
            html_3d = render_protein_ligand_complex(protein_pdb, ligand_pdbqt)
            return {"html": html_3d, "status": "success"}
        except ImportError as e:
            logger.error("Visualization import failed: %s", e)
            return {"status": "unavailable", "error": f"Missing dependency: {e}"}
        except Exception as e:
            logger.error("Visualization pipeline failed: %s", e)
            return {"status": "failed", "error": str(e)}
