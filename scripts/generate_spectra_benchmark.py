"""
scripts/generate_spectra_benchmark.py
======================================
Generates spectra_benchmark.csv by running IR, 1H NMR, and 13C NMR
heuristic predictors on each molecule in benchmark_molecules.csv, then
adding calibrated Gaussian noise to simulate experimental reference values.

IMPORTANT
---------
All "experimental" values produced by this script are HEURISTIC-DERIVED
(predicted + noise). They are NOT real experimental measurements.
This is clearly flagged in every output column and the source_notes field.

Noise parameters (conservative, matching typical measurement uncertainty):
    IR       : sigma = 25 cm⁻¹   (instrument resolution ~4 cm⁻¹, model error ~20)
    1H NMR   : sigma = 0.25 ppm  (shimming + heuristic error)
    13C NMR  : sigma = 3.0  ppm  (relaxation + heuristic error)
"""

from __future__ import annotations

import json
import logging
import os
import random
import sys
from pathlib import Path

import pandas as pd
from rdkit import Chem

# ── Path setup ─────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Use spec_from_file_location to import predictor files DIRECTLY,
# bypassing spectra/__init__.py which would re-trigger the circular chain.
import importlib.util as _ilu

def _load_module(name: str, rel_path: str):
    spec = _ilu.spec_from_file_location(name, ROOT / rel_path)
    mod  = _ilu.module_from_spec(spec)
    import sys as _sys
    _sys.modules.setdefault(name, mod)
    spec.loader.exec_module(mod)
    return mod

# functional_group_detector must be loaded first (ir_predictor depends on it)
_fgd_mod    = _load_module("spectra.functional_group_detector",
                            "spectra/functional_group_detector.py")
_ir_mod     = _load_module("spectra.ir_predictor",  "spectra/ir_predictor.py")
_proton_mod = _load_module("spectra.proton_nmr",     "spectra/proton_nmr.py")
_carbon_mod = _load_module("spectra.carbon_nmr",     "spectra/carbon_nmr.py")

predict_ir         = _ir_mod.predict_ir
predict_proton_nmr = _proton_mod.predict_proton_nmr
predict_carbon_nmr = _carbon_mod.predict_carbon_nmr

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Noise config ───────────────────────────────────────────────────────────────
IR_SIGMA     = 25.0   # cm⁻¹
PROTON_SIGMA = 0.25   # ppm
CARBON_SIGMA = 3.0    # ppm

SEED = 42
rng  = random.Random(SEED)


def _gauss(value: float, sigma: float) -> float:
    return round(value + rng.gauss(0, sigma), 2)


def _noisy_list(values: list[float], sigma: float) -> list[float]:
    return [_gauss(v, sigma) for v in values]


def _ir_midpoints(prediction) -> list[float]:
    """Extract mid-wavenumber for each IR band."""
    return [b.mid_cm for b in prediction.bands if b.mid_cm > 0]


def _proton_midpoints(prediction) -> list[float]:
    """Extract ppm_mid for each proton environment."""
    return [e.ppm_mid for e in prediction.environments if e.ppm_mid != 0]


def _carbon_midpoints(prediction) -> list[float]:
    """Extract ppm_mid for each carbon environment (atom-level)."""
    source = prediction.atom_environments or prediction.environments
    return [e.ppm_mid for e in source if e.ppm_mid != 0]


def process_molecule(smiles: str, name: str) -> dict | None:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        logger.warning("Invalid SMILES, skipping %s: %s", name, smiles)
        return None

    try:
        ir_pred     = predict_ir(mol)
        proton_pred = predict_proton_nmr(mol)
        carbon_pred = predict_carbon_nmr(mol)
    except Exception as exc:
        logger.warning("Prediction failed for %s: %s", name, exc)
        return None

    ir_mid     = _ir_midpoints(ir_pred)
    proton_mid = _proton_midpoints(proton_pred)
    carbon_mid = _carbon_midpoints(carbon_pred)

    # Add noise to simulate experimental reference values
    exp_ir     = sorted(_noisy_list(ir_mid,     IR_SIGMA),     reverse=True)
    exp_proton = sorted(_noisy_list(proton_mid, PROTON_SIGMA), reverse=True)
    exp_carbon = sorted(_noisy_list(carbon_mid, CARBON_SIGMA), reverse=True)

    return {
        "smiles":              smiles,
        "molecule_name":       name,
        "experimental_ir":     json.dumps(exp_ir),
        "experimental_proton": json.dumps(exp_proton),
        "experimental_carbon": json.dumps(exp_carbon),
        "n_ir_peaks":          len(exp_ir),
        "n_proton_peaks":      len(exp_proton),
        "n_carbon_peaks":      len(exp_carbon),
        # Heuristic provenance flags
        "ir_is_heuristic":     True,
        "proton_is_heuristic": True,
        "carbon_is_heuristic": True,
        "source_notes": (
            "HEURISTIC-DERIVED: experimental values simulated by adding Gaussian noise "
            f"(IR sigma={IR_SIGMA} cm⁻¹, 1H sigma={PROTON_SIGMA} ppm, "
            f"13C sigma={CARBON_SIGMA} ppm) to heuristic predictions. "
            "NOT real experimental data."
        ),
    }


def main() -> None:
    benchmark_csv = ROOT / "benchmark_molecules.csv"
    output_csv    = ROOT / "spectra_benchmark.csv"

    if not benchmark_csv.exists():
        logger.error("benchmark_molecules.csv not found at %s", benchmark_csv)
        sys.exit(1)

    df = pd.read_csv(benchmark_csv)
    df = df.dropna(subset=["smiles"])
    df = df[df["smiles"].str.strip() != ""]
    logger.info("Processing %d molecules …", len(df))

    rows = []
    for _, row in df.iterrows():
        result = process_molecule(
            smiles=str(row["smiles"]).strip(),
            name=str(row.get("name", row.get("compound_id", ""))),
        )
        if result:
            rows.append(result)

    out_df = pd.DataFrame(rows)
    out_df.to_csv(output_csv, index=False)
    logger.info(
        "Saved %d molecules to %s", len(out_df), output_csv
    )
    logger.info(
        "Mean peaks — IR: %.1f  1H: %.1f  13C: %.1f",
        out_df["n_ir_peaks"].mean(),
        out_df["n_proton_peaks"].mean(),
        out_df["n_carbon_peaks"].mean(),
    )


if __name__ == "__main__":
    main()
