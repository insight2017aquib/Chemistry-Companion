# Chemistry Companion

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![RDKit](https://img.shields.io/badge/rdkit-2023.03.1%2B-green)
![OpenBabel](https://img.shields.io/badge/openbabel-3.1.0-orange)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

**Chemistry Companion** is a robust, end-to-end open-source toolkit for structural analysis, heuristic spectral prediction (IR, ¹H NMR, ¹³C NMR), functional group detection, and docking preparation. 

Built on top of RDKit and Open Babel, it bridges the gap between bare-metal cheminformatics libraries and fully integrated batch workflows by providing natively structured outputs, comprehensive reporting (XLSX, Markdown), and publication-ready visualizations.

---

## 🌟 Key Features

1. **Heuristic Spectra Predictor**: Generates IR, ¹H NMR, and ¹³C NMR spectra from 2D structures using curated heuristic rules, with extensive tracking of atomic environments and multiplicity.
2. **Semantic Functional Group Detection**: Detects 27 curated functional group classes natively (unlike RDKit fragments which require manual categorization) using SMARTS.
3. **Automated Docking Preparation**: Wraps Open Babel to automatically assign 3D coordinates, optimize geometries (MMFF94), apply protonation states at physiological pH, compute Gasteiger charges, and export directly to `PDBQT` format for AutoDock Vina.
4. **Validation & Benchmarking Suites**: Ships with integrated tools to benchmark accuracy against experimental datasets, complete with confusion matrices and radar plots.
5. **Comprehensive Reporting**: Say goodbye to boilerplate pandas loops. Chemistry Companion natively exports multi-sheet styled XLSX workbooks, markdown summaries, and publication-ready Matplotlib/Seaborn plots.

---

## 🚀 Quick Start

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/aquibbelal/chemistry-companion.git](https://github.com/insight2017aquib/Chemistry-Companion
   cd chemistry-companion
   ```
2. (Optional but recommended) Create a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *Note: If you plan on using docking preparation, ensure you have Open Babel installed correctly. `openbabel-wheel` is provided in the requirements, but some platforms may require conda: `conda install -c conda-forge openbabel`.*

### Basic Usage (API)

A comprehensive API walkthrough is provided in `tutorial.ipynb`.

```python
from core.pipeline import ChemistryPipeline
from core.config import get_settings

pipeline = ChemistryPipeline(settings=get_settings())
result = pipeline.process_smiles('c1ccccc1') # Benzene

print(f"Descriptors computed: {len(result.descriptors.to_dict())}")
print(f"IR Prediction:\\n{result.ir_prediction.summary_text}")
```

---

## 📊 Reproducibility & Benchmarks

This repository serves as a **Publication Reproducibility Package**. It contains the scripts necessary to recreate all benchmarks, comparison tables, and figures.

### 1. Functional Group & Spectra Validation
Validates the heuristic spectra engines (IR, NMR) and functional group detection using synthetic/experimental benchmark data.

```bash
# Generates validation_report.md, validation_summary.xlsx, and 8 publication figures
python run_spectra_validation.py --input data/spectra_benchmark.csv --output outputs/spectra/
```

### 2. Tool Comparison Benchmark
Runs speed and feature comparisons between Chemistry Companion, RDKit, and Open Babel.
```bash
python scripts/run_tool_comparison.py
```
Outputs are saved to `outputs/comparison/` and include speed bar charts, feature radar plots, and Markdown/XLSX summaries.

---

## 📂 Example Datasets
The `data/` directory contains:
- `benchmark_molecules.csv`: A robust set of 61 diverse molecules.
- `spectra_benchmark.csv`: Molecules with attached experimental (or heuristically simulated) spectral peaks.
- `smiles_input.txt`: A minimal text file for quick batch testing.

---

## ⚠️ Limitations & Caveats

1. **Heuristic Limitations**: Spectral predictions are heuristic (rules-based), not quantum mechanical (DFT). They are exceptionally fast and great for educational/rapid screening purposes but **cannot replace empirical data or rigorous ab initio calculations** for novel chemical spaces.
2. **Stereochemistry**: The functional group detector and spectra predictors currently ignore stereochemistry (R/S, E/Z). All predictions are based on 2D topology.
3. **Open Babel Dependency**: Auto-generation of PDBQT files relies strictly on Open Babel's charge models. Ensure Open Babel bindings are properly compiled for your architecture.

---

## 📝 License & Citation

Distributed under the **MIT License**. See `LICENSE` for more information.

If you use Chemistry Companion in your research, please cite it using the provided `citation.cff` file.
