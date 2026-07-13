# Developability Architecture (Phase 10)

## 1. Objective
Create a Developability Analysis platform focusing on ADMET prediction, drug-likeness, and series comparison, tightly integrated with the existing MedChem Workbench.

## 2. Core Principles
- **Advisory Output**: ADMET heuristics and AI logic must distinctly separate *Observed* data (e.g. experimental IC50) from *Predicted* values (e.g. Heuristic BBB permeability) and *Hypotheses* (AI suggestions).
- **Zero Duplication**: ADMET metrics append to the existing `SeriesCompound` model's `properties` JSON. The Series manager acts as the foundation.

## 3. Components

### A. Persistence Layer (SQLite)
- **`SeriesCompound` model**: Append `"admet"` dictionary inside the existing `"properties"` JSON field. Stores PAINS/Brenk alerts, BBB probability, hERG risk, and Developability Rank.

### B. Service Layer
- **`AdmetService` (`services/admet_service.py`)**:
  - `predict_solubility(mw, logp, rot_bonds)`
  - `predict_permeability(tpsa, mw)`
  - `predict_bbb(logp, tpsa)`
  - `predict_herg_risk(logp, mw)`
  - `flag_toxicophores(smiles)`: PAINS (Pan Assay Interference Compounds) and Brenk alerts via RDKit SMARTS.
  - Generates text explanations alongside every prediction metric.
  - Calculates an overall `developability_score`.
- **`MedchemService` Extension**:
  - Add `calculate_admet_properties(smiles)` hooked into the compound insertion flow.

### C. AI Developability Expert
- **`AiDevelopabilityExpert` (`services/ai/developability_expert.py`)**:
  - `analyze_series_liabilities(series_id)`: Series-level liability analysis.
  - `suggest_optimization_targets(compound)`: Identifies precise optimization targets (e.g., "Decrease TPSA by 10 to improve Permeability").

### D. User Interface
- **`templates/medchem_workbench.html`**:
  - Add "Developability" Tab (Traffic lights for ADMET risks).
  - Add "PAINS/Brenk" alerts to SAR Table.
  - Add Radar Charts for Series Comparison.
