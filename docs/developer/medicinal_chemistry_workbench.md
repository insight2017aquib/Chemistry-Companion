# Medicinal Chemistry Workbench (Phase 9)

## Architecture

The Medicinal Chemistry Workbench provides a comprehensive dashboard for tracking Compound Series and performing Structure-Activity Relationship (SAR) analysis.

### Modules

1. **`services/medchem_service.py`**:
   - Integrates with RDKit to calculate fundamental physicochemical properties.
   - Computes Lipinski and Veber rule violations.
   - Computes `SAScore` (Synthetic Accessibility) if the RDKit contrib module is installed, mapping scores into High/Moderate/Low categorical feasibility.
   - Includes a heuristic for Matched Molecular Pair (MMP) detection using Maximum Common Substructure (MCS).

2. **`services/bioisostere_service.py`**:
   - A curated, rule-based engine that identifies known functional groups (e.g., Carboxylic Acid, Phenyl) via SMARTS matching.
   - Recommends classic bioisosteric replacements (e.g., Tetrazole, Pyridine) and explains the physicochemical logic.

3. **`services/ai/medchem_expert.py`**:
   - Analyzes aggregated series data to describe SAR trends.
   - Suggests analogs targeted at specific optimization goals (e.g., reducing lipophilicity).
   - Constrained by a system prompt to avoid hallucinating experimental binding affinities.

### Database Integration
- **`ChemicalSeries`**: Represents the optimization project.
- **`SeriesCompound`**: Stores individual compounds, their pIC50/IC50, docking affinity, and JSON blob of pre-computed properties.

## UI

- `templates/medchem_workbench.html` uses Alpine.js to manage tabs for SAR Tables, Plots, AI Chemist reports, and the Analog Designer.
- Seamlessly integrates with the Virtual Screening pipeline (`templates/virtual_screening.html`), which features a "Promote to MedChem" button on every hit.
