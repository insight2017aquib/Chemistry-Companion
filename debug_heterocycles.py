"""
debug_heterocycles.py
=====================
Advanced debug script for testing Proton + Carbon NMR
on complex heterocyclic and hybrid compounds.

Usage:
    python debug_heterocycles.py
"""

from rdkit import Chem
from spectra.proton_nmr import ProtonNMRPredictor
from spectra.carbon_nmr import CarbonNMRPredictor

# Initialize predictors
proton_predictor = ProtonNMRPredictor()
carbon_predictor = CarbonNMRPredictor(aggregate_equivalent=False)  # Show per-atom detail

# Complex heterocyclic & hybrid compounds
HETEROCYCLES = {
    "Quinoxaline":          "c1cc2nccnc2cc1",
    "Quinazoline":          "c1ccc2ncncc2cc1",
    "Caffeine":             "Cn1cnc2c1c(=O)n(c(=O)n2C)C",
    "Benzimidazole":        "c1ccc2[nH]cnc2c1",
    "Indole":               "c1ccc2[nH]ccc2c1",
    "Purine":               "c1ncnc2c1ncn2",
    "Quinoline":            "c1ccc2ncccc2c1",
    "Isoquinoline":         "c1ccc2cnccc2c1",
    "Pyrimidine":           "c1cncnc1",
    "Imidazole":            "c1cnc[nH]1",
    "Aspirin (for reference)": "CC(=O)Oc1ccccc1C(=O)O",
}

print("=" * 95)
print("HETEROCYCLIC & HYBRID COMPOUNDS - NMR DEBUG REPORT")
print("=" * 95)

for name, smi in HETEROCYCLES.items():
    print(f"\n{'='*95}")
    print(f"COMPOUND : {name}")
    print(f"SMILES   : {smi}")
    print("-" * 95)

    try:
        # === PROTON NMR ===
        proton_result = proton_predictor.predict_from_smiles(smi)
        print("\n[¹H NMR PREDICTION]")
        print(proton_result.summary())

        # === CARBON NMR ===
        carbon_result = carbon_predictor.predict_from_smiles(smi)
        print("\n[¹³C NMR PREDICTION]")
        print(carbon_result.summary())

        # === Extra Details (Carbon) ===
        print("\n[CARBON DETAILS - Per Environment]")
        for env in carbon_result.environments:
            print(f"  • {env.label:<30} | {env.ppm_range[0]:.1f}–{env.ppm_range[1]:.1f} ppm | {env.rationale}")

    except Exception as e:
        print(f"ERROR: {e}")

print("\n" + "=" * 95)
print("DEBUG REPORT COMPLETE")
print("=" * 95)