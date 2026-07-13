# Medicinal Chemistry Workbench Architecture (Phase 9)

## 1. Objective
Transform Chemistry Companion from a pure docking/screening tool into a full-fledged medicinal chemistry decision-support platform focusing on Structure-Activity Relationship (SAR), analog design, and lead optimization.

## 2. Core Concepts
- **Chemical Series**: A collection of related compounds (usually sharing a scaffold) being optimized towards a target.
- **SAR (Structure-Activity Relationship)**: The correlation between chemical structure modifications and biological activity (e.g., docking affinity, or experimental IC50 if provided).
- **Bioisosteres**: Chemical substituents with similar physical or chemical properties that produce broadly similar biological properties.

## 3. Architecture Constraints
- **Zero Duplication**: Do not build parallel pipelines for docking, visualization, or AI. Reuse `docking_workspace.html`, `pose_analysis.html`, `virtual_screening.html`, and `AI Docking Expert`.
- **No Speculation**: AI suggestions must rely on known medicinal chemistry rules (e.g., Hansch analysis, bioisosteric replacement) rather than hallucinating "magic" substituents.
- **Focus**: No Retrosynthesis. No Molecular Dynamics.

## 4. Components

### A. Persistence Layer (SQLite)
- **`ChemicalSeries` model**: `id`, `name`, `target_name`, `notes`, `created_at`.
- **`SeriesCompound` model**: `id`, `series_id`, `smiles`, `name`, `docking_score`, `activity_type`, `activity_value`, `activity_unit`, `normalized_value`, `properties` (JSON), `notes`, `tags` (JSON).

### B. Service Layer
- **`MedchemService` (`services/medchem_service.py`)**: 
  - Manage Series and Compounds CRUD.
  - Calculate RDKit properties (MW, LogP, TPSA, SAScore, Lipinski, Veber, Ghose, Egan, Muegge).
- **`ImportService` (`services/import_service.py`)**:
  - Uses `pandas` and `openpyxl` to parse CSV, SDF, Excel.
  - Normalizes units (e.g. uM to nM) and calculates standardized metrics (e.g. pIC50) based on `activity_type`.
- **`MMPEngine` (`services/mmp_service.py`)**:
  - Abstract interface identifying Matched Molecular Pairs using RDKit `rdFMCS`. Calculates $\Delta$Activity and $\Delta$Property.
- **`BioisostereService` (`services/bioisostere_service.py`)**:
  - Curated classic bioisosteres.
- **`ReportService` (`services/report_service.py`)**:
  - Generates Markdown templates: SAR, Series, Lead Optimization, Screening-to-Series.

### C. AI Medicinal Chemist Layer
- **`AiMedchemExpert` (`services/ai/medchem_expert.py`)**:
  - `analyze_sar(compounds)`: Distinguishes observed data from hypotheses.
  - `suggest_analogs(hit, target_profile)`: Suggests substitutions.

### D. User Interface
- **`medchem_workbench.html`**: Manage Series, SAR tables, Heatmaps, Data Import Modal.
- **Virtual Screening Dashboard**: Support for "Promote Hit", "Promote Top N", "Promote Scaffold Family".

## 5. System Flow
1. User imports data via CSV/Excel or promotes hits from Virtual Screening.
2. System calculates physical properties, normalizes biological activity, and identifies MMPs.
3. User analyzes heatmaps and property correlations in the UI.
4. AI Chemist interprets SAR and suggests analogs.
5. User exports a Markdown report.
