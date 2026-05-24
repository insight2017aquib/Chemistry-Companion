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
    from .protein_preparation import prepare_protein
    from .gridbox_builder import auto_gridbox, GridBoxConfig
    from .vina_runner import run_vina, VinaResult
    from .pose_manager import parse_vina_output, DockingPose
    from .interaction_mapper import map_interactions, Interaction
    from .report_builder import build_docking_report
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
    def auto_gridbox(*a, **kw):          raise RuntimeError(f"Docking unavailable: {_import_error}")
    def run_vina(*a, **kw):              raise RuntimeError(f"Docking unavailable: {_import_error}")
    def parse_vina_output(*a, **kw):     raise RuntimeError(f"Docking unavailable: {_import_error}")
    def map_interactions(*a, **kw):       raise RuntimeError(f"Docking unavailable: {_import_error}")
    def build_docking_report(*a, **kw):  raise RuntimeError(f"Docking unavailable: {_import_error}")

__all__ = [
    "prepare_protein",
    "auto_gridbox",
    "GridBoxConfig",
    "run_vina",
    "VinaResult",
    "parse_vina_output",
    "DockingPose",
    "map_interactions",
    "Interaction",
    "build_docking_report",
    "HAS_DOCKING",
]
