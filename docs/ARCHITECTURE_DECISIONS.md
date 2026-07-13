# Architecture Decisions (ADR Log)

This document tracks major architectural choices for Chemistry Companion.

## Core Stack Decisions
- **Backend Framework**: FastAPI (Python) - Chosen for high-performance async routing, auto-generated OpenAPI documentation, and straightforward JSON API creation.
- **Frontend Framework**: HTMX & Alpine.js with TailwindCSS - Chosen to keep logic simple and server-rendered. HTMX handles API routing and Alpine.js handles thick-client reactivity (like the docking workspace) without a complex Node/React build step.
- **Database**: SQLite via SQLAlchemy - Chosen for simplicity, local portability, and sufficient performance for a desktop scientific tool.
- **Visualization (Phase 4)**: Mol* (molstar) - Chosen for high-performance WebGL rendering of macromolecules directly in the browser. It integrates seamlessly with HTMX/Alpine.js via a zero-refresh architecture. Alpine handles the reactive UI state (checkboxes, gridbox inputs) and surgically updates the Mol* scene by calling specific plugin methods, avoiding expensive full-page re-renders.

## AI & Reasoning Module
- **Resilient AI Pipelines**: Multiple LLM providers are registered (`provider_manager.py`). The system is designed to fallback if Groq, DeepSeek, OpenRouter, or Gemini fail.
- **Structured Recommendation Engine**: AI modules don't just return strings; they return structured recommendations (e.g. for pockets, waters, chains) combined with a reasoning block.

## Scientific Domain Separation
- **Service Layer**: The `services/` layer orchestrates workflows and decouples the API from raw processing.
- **Domain Modules**: Modules like `docking_workflow` and `spectra` are strictly separated from HTTP concepts. They rely on dataclasses and return structured domain objects.
- **Protein Analysis Engine (Phase 3)**: Deep heuristic analysis (Chain, Water, Metal, Cofactor, Quality Assessment) is built as a pure scientific layer (`docking_workflow/protein_analysis.py`), completely divorced from GUI state, providing structured metadata for the frontend and AI tools via isolated `/api/docking/protein/*` endpoints.

## Workspace Persistence (Phase 1)
- **Hybrid Storage Model**: The `WorkspaceManager` service stores lightweight state and metadata in the SQLite `workspaces` table for quick querying and project indexing. Heavy blobs (like megabytes of PDB text) are written directly to the file system (`outputs/workspaces/{id}/`) to prevent database bloat and ensure fast transaction times.
- **Frontend State Recovery**: The HTMX/Alpine.js frontend leverages a local cache (`localStorage`) for immediate synchronous saves (protecting against sudden network drops), coupled with a debounced backend API for long-term project persistence.

## Workstation Integration (Phase 4)
- **Unified 2-Column Design**: The Protein Preparation Workspace is consciously integrated directly into the `docking_workspace.html` wizard rather than a fragmented multi-page layout. The left pane functions as the primary interaction area (Chain, Water, Pocket, Metal controls), and the right pane strictly houses the persistent Mol* viewer, ensuring visual state is always perfectly synced with scientific preparation steps.

## Docking Command Center (Phase 6)
- **Unified Execution & Inspection Flow**: Rather than treating Vina execution as a separate silo, the Command Center fuses the Phase 4 Preparation Workspace with a Job Manager. When Vina is launched, it runs asynchronously in the backend, while Alpine.js streams the standard output and progress to the user.
- **Decoupled Pose Analysis**: Once docking is complete, the workflow seamlessly hands off to `pose_analysis.html`. This separation ensures the Docking Workspace (`docking_workspace.html`) is dedicated to *preparation and execution*, while Pose Analysis provides a dedicated viewport (using Mol* and the `interaction_analyzer.py` engine) for rigorous medicinal chemistry inspection without cluttering the setup interface.

## AI Docking Expert (Phase 7)
- **Scientific Truth Separation**: The AI layer (`services/ai/docking_expert.py`) strictly interprets pre-calculated deterministic results from the physics engine (affinities, interactions, RMSD). System prompts are explicitly configured to forbid the LLM from overriding rank order or inventing contacts, ensuring the tool remains scientifically robust while still providing conversational SAR insights.
