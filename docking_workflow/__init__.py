"""
docking_workflow/__init__.py
============================
Docking Workflow module for Vina preparation, execution, and analysis.
All heavy dependencies (vina, meeko, openbabel) are optional.
"""

import logging

logger = logging.getLogger(__name__)

HAS_DOCKING = False
_import_error = ""

try:
    from .protein_preparation import prepare_protein, prepare_flexible_receptor
    from .gridbox_builder import auto_gridbox, GridBoxConfig
    from .vina_runner import run_vina, VinaResult, rescore_pose
    from .pose_manager import parse_vina_output, DockingPose
    from .interaction_mapper import map_interactions, Interaction
    from .interaction_analyzer import find_interactions
    from .interaction_fingerprint import compare_interactions, reference_ligand_interactions
    from .chimera_exporter import get_chimera_script_for_job, create_chimera_bundle
    from .report_builder import build_docking_report, affinity_to_pkd
    from .protein_analysis import analyze_protein, ProteinAnalysis, ChainInfo
    from .redock_validation import redock_validate, RedockValidationResult
    HAS_DOCKING = True
except ImportError as e:
    _import_error = str(e)
    logger.warning("Docking workflow module partially unavailable: %s", e)

    # Provide minimal stubs and dataclass stand-ins so imports never crash
    class GridBoxConfig:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    class VinaResult:
        pdbqt_output: str = ""

    class DockingPose:
        pass

    class Interaction:
        pass

    def prepare_protein(*a, **kw):       raise RuntimeError(f"Docking unavailable: {_import_error}")
    def prepare_flexible_receptor(*a, **kw): raise RuntimeError(f"Docking unavailable: {_import_error}")
    def auto_gridbox(*a, **kw):          raise RuntimeError(f"Docking unavailable: {_import_error}")
    def run_vina(*a, **kw):              raise RuntimeError(f"Docking unavailable: {_import_error}")
    def rescore_pose(*a, **kw):          raise RuntimeError(f"Docking unavailable: {_import_error}")
    def parse_vina_output(*a, **kw):     raise RuntimeError(f"Docking unavailable: {_import_error}")
    def map_interactions(*a, **kw):       raise RuntimeError(f"Docking unavailable: {_import_error}")
    def find_interactions(*a, **kw):      raise RuntimeError(f"Docking unavailable: {_import_error}")
    def compare_interactions(*a, **kw):   raise RuntimeError(f"Docking unavailable: {_import_error}")
    def reference_ligand_interactions(*a, **kw): raise RuntimeError(f"Docking unavailable: {_import_error}")
    def get_chimera_script_for_job(*a, **kw): raise RuntimeError(f"Docking unavailable: {_import_error}")
    def create_chimera_bundle(*a, **kw):  raise RuntimeError(f"Docking unavailable: {_import_error}")
    def build_docking_report(*a, **kw):  raise RuntimeError(f"Docking unavailable: {_import_error}")
    def affinity_to_pkd(*a, **kw):       raise RuntimeError(f"Docking unavailable: {_import_error}")
    def analyze_protein(*a, **kw):       raise RuntimeError(f"Docking unavailable: {_import_error}")
    def redock_validate(*a, **kw):       raise RuntimeError(f"Docking unavailable: {_import_error}")

    class RedockValidationResult:
        pass

__all__ = [
    "prepare_protein",
    "prepare_flexible_receptor",
    "auto_gridbox",
    "GridBoxConfig",
    "run_vina",
    "VinaResult",
    "rescore_pose",
    "parse_vina_output",
    "DockingPose",
    "map_interactions",
    "Interaction",
    "find_interactions",
    "compare_interactions",
    "reference_ligand_interactions",
    "get_chimera_script_for_job",
    "create_chimera_bundle",
    "build_docking_report",
    "affinity_to_pkd",
    "analyze_protein",
    "ProteinAnalysis",
    "ChainInfo",
    "redock_validate",
    "RedockValidationResult",
    "HAS_DOCKING",
]
