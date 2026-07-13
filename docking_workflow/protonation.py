"""
docking_workflow/protonation.py
==============================

Phase 7: Protonation Pipeline for Receptor Preparation.

Provides optional pH-dependent protonation and hydrogen addition
using PDB2PQR (which can internally use PropKa for pKa predictions).

This is designed to be optional and graceful:
- If PDB2PQR is not installed, the function returns the original text with a warning.
- Intended to run early in the preparation pipeline, before OpenBabel.

Typical usage:
    protonated_pdb = protonate_receptor(pdb_text, ph=7.4)
    then pass to prepare_receptor(...)
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)


def is_pdb2pqr_available() -> bool:
    """Check if the pdb2pqr command is available in PATH."""
    return shutil.which("pdb2pqr") is not None


def protonate_receptor(
    pdb_text: str,
    ph: float = 7.4,
    force_field: str = "AMBER",
    timeout: int = 120
) -> str:
    """
    Run pH-dependent protonation on a receptor using PDB2PQR.

    Parameters
    ----------
    pdb_text : str
        Raw PDB content.
    ph : float
        Target pH for protonation (default 7.4).
    force_field : str
        Force field to use (AMBER, CHARMM, etc.). PDB2PQR default is often AMBER.
    timeout : int
        Maximum seconds to allow PDB2PQR to run.

    Returns
    -------
    str
        Protonated PDB text. If PDB2PQR is unavailable or fails,
        the original pdb_text is returned with a logged warning.
    """
    if not is_pdb2pqr_available():
        logger.warning(
            "PDB2PQR not found in PATH. Skipping receptor protonation. "
            "Install with: conda install -c conda-forge pdb2pqr"
        )
        return pdb_text

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.pdb")
        output_path = os.path.join(tmpdir, "protonated.pdb")

        with open(input_path, "w", encoding="utf-8") as f:
            f.write(pdb_text)

        cmd = [
            "pdb2pqr",
            f"--ff={force_field}",
            f"--pdb-output={output_path}",
            f"--pH={ph}",
            "--keep-chain",
            "--titration-state-method=propka",  # Use PropKa for better pKa predictions
            input_path,
            output_path.replace(".pdb", ".pqr")  # PDB2PQR still needs a PQR output path
        ]

        try:
            logger.info(f"Running PDB2PQR protonation at pH={ph}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmpdir
            )

            if result.returncode != 0:
                logger.warning("PDB2PQR failed (returncode=%s): %s", result.returncode, result.stderr)
                return pdb_text

            if not os.path.exists(output_path):
                logger.warning("PDB2PQR did not produce expected output file.")
                return pdb_text

            with open(output_path, "r", encoding="utf-8") as f:
                protonated = f.read()

            logger.info("Receptor protonation completed successfully with PDB2PQR + PropKa.")
            return protonated

        except subprocess.TimeoutExpired:
            logger.error("PDB2PQR timed out after %s seconds", timeout)
            return pdb_text
        except Exception as e:
            logger.exception("Unexpected error during PDB2PQR protonation: %s", e)
            return pdb_text


def get_protonation_info(ph: float) -> dict:
    """Helper to return metadata about the protonation step."""
    return {
        "ph": ph,
        "tool": "pdb2pqr + propka" if is_pdb2pqr_available() else "none (skipped)",
        "available": is_pdb2pqr_available()
    }
