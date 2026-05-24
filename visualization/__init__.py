"""
visualization/__init__.py
=========================
Visualization module for rendering proteins, ligands, and complexes.
All heavy dependencies (gemmi, rdkit, py3Dmol) are optional.
"""

import logging

logger = logging.getLogger(__name__)

# Check optional dependencies individually for robust and helpful reporting
missing_deps = []

try:
    import pydantic
except ImportError:
    missing_deps.append("pydantic")

try:
    import gemmi
except ImportError:
    missing_deps.append("gemmi")

try:
    import rdkit
except ImportError:
    missing_deps.append("rdkit")

try:
    import py3Dmol
except ImportError:
    missing_deps.append("py3Dmol")

HAS_VISUALIZATION = (len(missing_deps) == 0)

if HAS_VISUALIZATION:
    try:
        from .viewer_models import ProteinViewerData, LigandViewerData, ComplexViewerData, ViewerStyle
        from .protein_loader import load_protein_pdb
        from .ligand_renderer_2d import render_ligand_2d
        from .ligand_renderer_3d import render_ligand_3d
        from .complex_renderer import render_protein_ligand_complex
        from .viewer_service import VisualizationOrchestrator
        _import_error = ""
    except Exception as e:
        HAS_VISUALIZATION = False
        _import_error = f"Error importing rendering components: {str(e)}"
        logger.exception("Visualization module import failed:")
else:
    _import_error = f"Missing dependency/dependencies: {', '.join(missing_deps)}"
    logger.warning("Visualization module partially unavailable. Missing: %s", ", ".join(missing_deps))

# Provide safe stubs so downstream code can import names without crashing
if not HAS_VISUALIZATION:
    # Stubs for Pydantic models
    class ViewerStyle:
        def __init__(self, *args, **kwargs): pass
        def dict(self): return {}

    class ProteinViewerData:
        def __init__(self, *args, **kwargs): pass
        def dict(self): return {}

    class LigandViewerData:
        def __init__(self, *args, **kwargs): pass
        def dict(self): return {}

    class ComplexViewerData:
        def __init__(self, *args, **kwargs): pass
        def dict(self): return {}

    # Stubs for rendering functions
    def load_protein_pdb(*a, **kw):          raise RuntimeError(f"Visualization unavailable. {_import_error}")
    def render_ligand_2d(*a, **kw):          raise RuntimeError(f"Visualization unavailable. {_import_error}")
    def render_ligand_3d(*a, **kw):          raise RuntimeError(f"Visualization unavailable. {_import_error}")
    def render_protein_ligand_complex(*a, **kw): raise RuntimeError(f"Visualization unavailable. {_import_error}")

    class VisualizationOrchestrator:
        @staticmethod
        def process_protein(*a, **kw):  raise RuntimeError(f"Visualization unavailable. {_import_error}")
        @staticmethod
        def process_ligand(*a, **kw):   raise RuntimeError(f"Visualization unavailable. {_import_error}")
        @staticmethod
        def render_complex(*a, **kw):   raise RuntimeError(f"Visualization unavailable. {_import_error}")

__all__ = [
    "ProteinViewerData",
    "LigandViewerData",
    "ComplexViewerData",
    "ViewerStyle",
    "load_protein_pdb",
    "render_ligand_2d",
    "render_ligand_3d",
    "render_protein_ligand_complex",
    "VisualizationOrchestrator",
    "HAS_VISUALIZATION",
]
