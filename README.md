# Chemistry Companion

![Version](https://img.shields.io/badge/version-3.0.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![RDKit](https://img.shields.io/badge/rdkit-2023.03.1%2B-green)
![OpenBabel](https://img.shields.io/badge/openbabel-3.1.0-orange)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

**Chemistry Companion 3.0** is an integrated open-source research workbench for molecular analysis, heuristic spectral prediction (IR, ¹H / ¹³C NMR), functional-group detection, docking preparation and execution (AutoDock Vina), virtual screening, and medicinal-chemistry research workflows.

Built on **RDKit** and **Open Babel**, it combines a Python library API, a FastAPI web UI, packaging for `pip`, a portable PyInstaller build, and a Windows installer.

---

## Key features

1. **Heuristic spectra** — IR, ¹H NMR, ¹³C NMR from 2D structure (rules-based, educational / screening speed)
2. **Functional groups** — curated SMARTS classes with structured reports
3. **Docking prep & workspace** — 3D embed, protonation, PDBQT, grid, Vina, pose analysis
4. **Research tools** — Virtual Screening, MedChem, ADMET, Lead Optimization, Research OS, Publication Assistant, Knowledge Engine
5. **Exports** — CSV, JSON, multi-sheet Excel, publication-oriented plots
6. **Optional AI** — multi-provider LLM explanations with deterministic fallback when keys are missing

---

## Install options

### A. Windows installer (end users — no Python required)

1. Run `ChemistryCompanion-3.0.0-Setup.exe` from the release assets (or `dist/installer/` after building).
2. Accept the MIT license, choose install directory, enable desktop/Start Menu shortcuts.
3. Prefer a **writable** location (e.g. current-user / `%LOCALAPPDATA%\Programs\Chemistry Companion`).
4. Launch **Chemistry Companion** — complete or skip the **First Run** setup wizard.
5. Browser opens to `http://127.0.0.1:8000` (leave the console window open while working).

See `windows_installer.md`, `installer_validation.md`, and `release_notes_v3.md`.

### B. Portable onedir (no installer)

```text
dist/ChemistryCompanion/ChemistryCompanion.exe
```

See `pyinstaller_report.md`.

### C. Python package (developers)

```bash
git clone https://github.com/aquibbelal/chemistry-companion.git
cd chemistry-companion
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
# or: pip install -r requirements.txt
```

**CLI**

```bash
chemistry-companion version
chemistry-companion analyse --smiles c1ccccc1
```

**Web server**

```bash
chemistry-companion-server
# or: python -m api
# or: uvicorn api.app:app --host 127.0.0.1 --port 8000
```

**Library**

```python
from core.pipeline import ChemistryPipeline
from core.config import get_settings

pipeline = ChemistryPipeline(settings=get_settings())
result = pipeline.process_smiles("c1ccccc1")
print(result.descriptors)
```

Optional docking: ensure AutoDock Vina CLI is available (`VINA_BINARY` or PATH).  
Open Babel is provided via `openbabel-wheel` (conda-forge alternative on some platforms).

---

## Configuration

**Recommended:** use the **First Run Experience** (or **Settings → Setup Wizard**) to create `.env` and choose an AI provider — or skip AI entirely.

Alternatively, copy `.env.example` to `.env` for optional LLM keys and overrides:

```text
APP_VERSION=3.0.0
AI_PROVIDER=disabled
OPENROUTER_API_KEY=...
# OPENAI_API_KEY / GROQ_API_KEY / Ollama settings
```

Prefix: `CHEM_COMPANION_` with nested `__` where applicable (see `core/config.py` and `.env.example`).

---

## Documentation

| Document | Purpose |
|----------|---------|
| `CHANGELOG.md` | Version history |
| `CREDITS.md` | Authors and third-party stack |
| `LICENSE` | MIT license |
| `citation.cff` | Citation metadata |
| `docs/` | Architecture and developer guides |
| `release_notes_v3.md` | Public release notes |
| `release_summary.md` | Executive release summary |
| `release_gate.md` | Release readiness gate |
| `first_run_experience.md` | Setup wizard design |
| `installer_validation.md` | Windows installer acceptance |
| `portable_release_validation.md` | Portable build smoke |
| `packaging_foundation.md` | Python packaging |
| `windows_installer.md` | Installer design |
| `tutorial.ipynb` | API walkthrough |

---

## Benchmarks & data

- `data/benchmark_molecules.csv` — diverse molecule set  
- `data/spectra_benchmark.csv` — spectra validation inputs  
- `data/smiles_input.txt` — quick batch sample  

---

## Limitations

1. Spectral predictions are **heuristic**, not quantum/DFT or experimental replacements.  
2. Stereochemistry is largely ignored in FG/spectra heuristics (2D topology).  
3. Full docking/screening requires a working **Vina** binary and suitable receptor prep (bundled in Windows builds).  
4. Web UI styling/components use **CDN** assets (internet recommended).  
5. IUPAC via OPSIN needs a **JRE** at runtime.  
6. Windows Setup/EXE are not Authenticode-signed (SmartScreen may warn on first run).

---

## License & citation

Distributed under the **MIT License** — see `LICENSE`.

Cite using `citation.cff` (version **3.0.0**). Author: **Aquib Belal**.

---

## Credits

See `CREDITS.md` for the full scientific and web stack acknowledgments.
