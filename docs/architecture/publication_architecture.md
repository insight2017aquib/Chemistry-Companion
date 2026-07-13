# Publication & Thesis Architecture (Phase 13)

## 1. Objective
Provide a dedicated platform to transform the structured data and Knowledge Graph of the Research OS into publication-ready manuscripts, tables, figures, and reproducibility packages.

## 2. Core Concepts
- **Report Builder**: Assembles structured data (SAR, ADMET, Docking) into comprehensive Markdown/LaTeX/HTML documents.
- **Table Generator**: Converts data into Markdown, LaTeX, and CSV formats.
- **Citation Manager**: Formats stored `LiteratureReference` entries into standard styles (ACS, Nature, APA) using programmatic string formatting.
- **AI Scientific Writer**: Drafts "Results" and "Methods" sections with strict evidence linking. Every claim must reference a Project ID, Campaign ID, or Compound ID.
- **Reproducibility Package**: A JSON or zip payload detailing exactly what software versions (RDKit, Vina), parameters, and grid boxes were used to generate the data.

## 3. Database Schema Extensions
In accordance with the `database_evolution.md` strategy, we will add new tables:
- **`PublicationDraft`**: `id`, `project_id`, `title`, `content_type` (Results, Discussion, Full), `content` (Markdown), `status`, `created_at`.
- **`ReproducibilityLog`**: `id`, `project_id`, `experiment_id`, `software_versions` (JSON), `parameters` (JSON).

## 4. Components

### A. Service Layer
- **`PublicationService` (`services/publication_service.py`)**: Handles generation of tables (Markdown/LaTeX), building the Reproducibility Package, and formatting Citations.
- **`CitationService`**: Embedded within `PublicationService`. Formats stored `LiteratureReference` DOIs into text strings based on requested styles.

### B. AI Scientific Writer
- **`AiScientificWriter` (`services/ai/scientific_writer.py`)**:
  - `draft_results(campaign_data)`: Writes the results section, strictly citing compound IDs and actual MPO values.
  - `draft_methods(reproducibility_data)`: Converts parameter JSONs into standard academic methodology paragraphs.

### C. UI & Visualization
- **`templates/publication_studio.html`**:
  - **Manuscript Builder**: Text editor with AI-assisted drafting blocks.
  - **Table Export Hub**: Export SAR/Docking tables directly to `.csv` or `.tex`.
  - **Figure Builder**: Uses Chart.js (or Plotly if added) to generate and download high-res PNG charts for properties and campaign timelines.
  - **Citation Manager**: View all literature formatted dynamically.
