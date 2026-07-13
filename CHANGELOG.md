# Changelog

All notable changes to Chemistry Companion are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] — 2026-07-13

Public research-platform release: integrated workbench, First Run Experience, packaging, portable build, and Windows installer.

**Build:** `20260713.2254`  
**Ship artifact:** `ChemistryCompanion-3.0.0-Setup.exe`

### Added

- Full web workbench (FastAPI + Jinja2): Dashboard, Analysis, Batch, Spectra, History, Settings
- Advanced docking workspace (protein prep, grid, AutoDock Vina, pose analysis, ChimeraX handoff)
- Protein Asset Management System (PAMS): RCSB fetch, upload, local files
- Research tools: Virtual Screening, MedChem, ADMET, Lead Optimization, Research OS, Publication Assistant, Knowledge Engine
- **First Run Experience (FRE)** — setup wizard on first launch; skip AI; configure OpenRouter / OpenAI / Groq / Ollama / disabled without hand-editing `.env`
- AI provider manager with template fallback when keys are missing
- Production `pyproject.toml` packaging (`chemistry-companion` 3.0.0)
- Freeze-safe resource paths (`core/paths.py`) and portable entry (`portable_entry.py`)
- PyInstaller **onedir** portable build (`ChemistryCompanion.exe`)
- Windows **Inno Setup** installer: MIT license page, icon, desktop/Start Menu shortcuts, uninstaller; user data preserved on upgrade and uninstall
- Release documentation suite (packaging, portable, installer, FRE, acceptance, release gate)

### Changed

- Virtual Screening ligand prep and docking use **real** `prepare_docking_structure` + AutoDock Vina (no random mock affinities)
- Version strings unified to **3.0.0** across package, API, CLI, FRE, config, citation, and installer
- Settings and setup wizard aligned for re-entry after first completion

### Fixed

- Screening start requires a prepared receptor PDBQT from the workspace (no `mock_receptor.pdbqt` fallback)
- LLM docking explainer prompt wording (removed “Mocked” label)
- Installer uninstall no longer wipes user research data by design

### Known limitations

- Spectral predictions are **heuristic**, not DFT or experimental substitutes
- UI chrome loads Tailwind/HTMX/Alpine/Plotly/3Dmol from CDN (internet recommended)
- JSON `POST /api/analyze` has a known descriptor serialization issue; the web analysis form works
- Windows Setup/EXE are not Authenticode-signed (SmartScreen may warn)
- Default admin install under Program Files may require a writable data path (prefer current-user install under `%LOCALAPPDATA%\Programs\…`)
- Console window is visible in the portable/installer EXE (support-friendly)

## [1.0.0] — 2026-05-20

Initial publication-oriented toolkit release (pipeline, spectra, descriptors, citation).

See also historical notes in `docs/changelog/`.

[3.0.0]: https://github.com/aquibbelal/chemistry-companion/releases/tag/v3.0.0
[1.0.0]: https://github.com/aquibbelal/chemistry-companion/releases/tag/v1.0.0
