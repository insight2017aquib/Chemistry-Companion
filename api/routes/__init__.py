"""
api/routes/__init__.py
======================
Routes initialization.
"""

from .analysis import router as analysis_router
from .batch import router as batch_router
from .export import router as export_router
from .spectra import router as spectra_router

__all__ = [
    "analysis_router",
    "batch_router",
    "export_router",
    "spectra_router",
]