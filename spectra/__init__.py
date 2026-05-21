"""
spectra package
===============

Heuristic spectral prediction modules for Chemistry Companion.

This package exposes:
- functional group detection
- IR prediction
- 1H NMR prediction
- 13C NMR prediction
"""

from .carbon_nmr import (
    CarbonEnvironment,
    CarbonNMRPrediction,
    CarbonNMRPredictor,
)
from .functional_group_detector import (
    FGDefinition,
    FGMatch,
    FGReport,
    FunctionalGroupDetector,
    detect_functional_groups,
)
from .ir_predictor import (
    IRBand,
    IRPeak,
    IRPrediction,
    IRPredictor,
)
from .proton_nmr import (
    NMRPrediction,
    ProtonNMRPredictor,
)

__all__ = [
    "CarbonEnvironment",
    "CarbonNMRPrediction",
    "CarbonNMRPredictor",
    "FGDefinition",
    "FGMatch",
    "FGReport",
    "FunctionalGroupDetector",
    "IRBand",
    "IRPeak",
    "IRPrediction",
    "IRPredictor",
    "NMRPrediction",
    "ProtonNMRPredictor",
    "detect_functional_groups",
]