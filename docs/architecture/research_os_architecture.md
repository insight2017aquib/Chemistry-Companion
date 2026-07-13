# Research Operating System Architecture (Phase 12)

## 1. Objective
Transform Chemistry Companion from a disparate suite of computational tools into a cohesive Research Operating System (Research OS). This layer introduces project management, scientific memory, and literature tracking without duplicating any of the underlying data structures.

## 2. Core Concepts
- **Project**: The master entity. A Project contains Portfolios, Notebook Entries, Literature, and overarching Objectives.
- **Scientific Notebook**: A chronological ledger of observations, hypotheses, and conclusions attached to Projects or specific Campaigns.
- **Literature Manager**: A repository for external research (PMID, DOI) linked directly to internal hypotheses or compound designs.
- **Knowledge Graph**: The conceptual web linking Papers $\rightarrow$ Projects $\rightarrow$ Campaigns $\rightarrow$ Series $\rightarrow$ Compounds $\rightarrow$ Decisions.
- **Reporting Engine**: Automated generation of structured Markdown/HTML tables for thesis writing or supervisor updates.

## 3. Database Schema Extensions
In accordance with the `database_evolution.md` strategy, these will be new tables to avoid schema migration conflicts:
- **`ResearchProject`**: `id`, `name`, `objectives`, `target`, `status`, `created_at`.
- **`NotebookEntry`**: `id`, `project_id`, `entity_type` (Campaign/Series/Compound), `entity_id`, `entry_type` (Observation/Hypothesis/Result), `content`, `date`.
- **`LiteratureReference`**: `id`, `project_id`, `doi`, `pmid`, `title`, `authors`, `notes`.
- **`ProjectPortfolioLink`**: Maps `Portfolio` entities (from Phase 11) to `ResearchProject`.

## 4. Components

### A. Service Layer
- **`ProjectService` (`services/project_service.py`)**: CRUD for Projects, Notebooks, and Literature.
- **`KnowledgeGraphService` (`services/knowledge_graph.py`)**: Traverses relations (e.g., fetching all Decisions, Notebook Entries, and Literature associated with a specific Campaign).
- **`ReportEngine` (`services/report_engine.py`)**: Aggregates data across the Knowledge Graph to build exportable tables (SAR, Docking, ADMET) formatted for academic thesis support.

### B. AI Research Assistant
- **`AiResearchAssistant` (`services/ai/research_assistant.py`)**:
  - `summarize_project(project_id)`: Synthesizes notebook entries, decisions, and campaign metrics into a high-level executive summary.
  - `review_hypotheses(project_id)`: Analyzes recorded hypotheses against actual MPO/Activity outcomes to extract "Lessons Learned".

### C. UI & Visualization
- **`templates/research_os.html`**:
  - **Project Hub**: High-level status of targets and milestones.
  - **Notebook UI**: Rich text or Markdown editor for daily scientific logging.
  - **Literature Tracker**: Simple table managing DOIs/PMIDs and personal notes.
  - **Report Generator**: One-click generation of Thesis-ready compound tables.
