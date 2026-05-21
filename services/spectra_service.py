"""
services/spectra_service.py
==========================
Service layer for spectral analysis operations.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from spectra.ir_predictor import IRPredictor
from spectra.proton_nmr import ProtonNMRPredictor
from spectra.carbon_nmr import CarbonNMRPredictor

logger = logging.getLogger(__name__)


class SpectraService:
    """Service for handling spectral prediction operations."""

    def __init__(self):
        self.ir_predictor = IRPredictor()
        self.proton_predictor = ProtonNMRPredictor()
        self.carbon_predictor = CarbonNMRPredictor()

    def predict_ir(self, mol: Any) -> Optional[Any]:
        """
        Predict IR spectrum for a molecule.

        Args:
            mol: RDKit molecule object

        Returns:
            IR prediction result or None
        """
        try:
            if mol is None:
                return None
            return self.ir_predictor.predict(mol)
        except Exception as e:
            logger.warning(f"IR prediction failed: {e}")
            return None

    def predict_proton_nmr(self, mol: Any) -> Optional[Any]:
        """
        Predict ¹H NMR spectrum for a molecule.

        Args:
            mol: RDKit molecule object

        Returns:
            Proton NMR prediction result or None
        """
        try:
            if mol is None:
                return None
            return self.proton_predictor.predict(mol)
        except Exception as e:
            logger.warning(f"¹H NMR prediction failed: {e}")
            return None

    def predict_carbon_nmr(self, mol: Any) -> Optional[Any]:
        """
        Predict ¹³C NMR spectrum for a molecule.

        Args:
            mol: RDKit molecule object

        Returns:
            Carbon NMR prediction result or None
        """
        try:
            if mol is None:
                return None
            return self.carbon_predictor.predict(mol)
        except Exception as e:
            logger.warning(f"¹³C NMR prediction failed: {e}")
            return None

    def predict_all_spectra(self, mol: Any) -> dict[str, Any]:
        """
        Predict all spectra for a molecule.

        Args:
            mol: RDKit molecule object

        Returns:
            Dictionary with all spectral predictions
        """
        return {
            "ir": self.predict_ir(mol),
            "proton_nmr": self.predict_proton_nmr(mol),
            "carbon_nmr": self.predict_carbon_nmr(mol),
        }