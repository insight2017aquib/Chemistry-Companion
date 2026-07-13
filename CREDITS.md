# Credits

## Author / maintainer

- **Aquib Belal** — design, implementation, and release of Chemistry Companion

## Core scientific stack

| Component | Role | License (typical) |
|-----------|------|-------------------|
| [RDKit](https://www.rdkit.org/) | Cheminformatics, descriptors, 2D depiction | BSD |
| [Open Babel](https://openbabel.org/) | Format conversion, 3D, protonation, PDBQT | GPL-2.0-or-later |
| [AutoDock Vina](https://vina.scripps.edu/) | Molecular docking | Apache-2.0 |
| [Meeko](https://github.com/forlilab/Meeko) | Ligand PDBQT preparation | LGPL |
| [Gemmi](https://gemmi.readthedocs.io/) | Macromolecular structure I/O | MPL-2.0 |
| [PubChemPy](https://pubchempy.readthedocs.io/) | PubChem name/structure resolution | MIT |
| [OPSIN / py2opsin](https://github.com/dan2097/opsin) | IUPAC name → SMILES (requires JRE) | Artistic / related |

## Web & data stack

| Component | Role |
|-----------|------|
| FastAPI / Starlette / Uvicorn | HTTP API and ASGI server |
| Jinja2 | HTML templating |
| SQLAlchemy / SQLite | Persistence |
| Pydantic / pydantic-settings | Validation and configuration |
| Pandas / NumPy / SciPy | Numerics and tables |
| Matplotlib / Seaborn | Figures and reports |
| openpyxl | Excel export |

## Frontend (CDN)

| Component | Role |
|-----------|------|
| Tailwind CSS | Styling |
| HTMX | Progressive HTML interactions |
| Alpine.js | Client UI state |
| Plotly / Chart.js / vis-network | Charts and graphs |
| 3Dmol.js | Molecular 3D visualization |

## Packaging & distribution (v3)

| Component | Role |
|-----------|------|
| PyInstaller | Portable onedir Windows build |
| Inno Setup 6 | Windows installer (`ChemistryCompanion-3.0.0-Setup.exe`) |
| Uvicorn | Production ASGI server for desktop launch |

## Acknowledgments

- Open-source cheminformatics and docking communities that maintain RDKit, Open Babel, and AutoDock Vina
- Contributors of benchmark ideas and validation datasets shipped under `data/`

## Citation

If you use Chemistry Companion in research, please cite using `citation.cff` (version **3.0.0**, released 2026-07-13).
