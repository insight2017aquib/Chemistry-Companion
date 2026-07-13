# Development Rules for Chemistry Companion

This document establishes the ground rules for all future development and AI-assisted programming in this repository.

## 1. Do Not Nuke Scripts
- **Rule**: When modifying complex UI scripts (e.g., `docking_workspace.html`), you must apply **surgical changes**.
- **Reason**: These files contain deeply interconnected Alpine.js state machines and HTMX wiring. Overwriting them completely risks breaking unrelated features.

## 2. Maintain Architectural Boundaries
- **Rule**: Never place scientific logic directly in the FastAPI API routers (`api/`). 
- **Reason**: All domain logic must reside in `core/`, `docking_workflow/`, or `spectra/`, and be orchestrated by `services/`. API routers are strictly for HTTP request parsing and response formatting.

## 3. Frontend Technology Constraints
- **Rule**: Do not introduce React, Vue, or heavy node-based build systems.
- **Reason**: The project relies on HTMX for server-rendered interactions and Alpine.js for lightweight client-side state. TailwindCSS is used for styling. Stick to these technologies to maintain the project's lightweight profile.

## 4. AI Tooling Requirements
- **Rule**: When calling external LLM APIs, use the established `provider_manager.py` instead of raw API calls.
- **Reason**: The provider manager ensures resilient fallback chains (Groq -> DeepSeek -> OpenRouter -> Gemini) so the platform remains stable during API outages.

## 5. Documentation
- **Rule**: Ensure that any new endpoints or core workflows are documented in `docs/developer/`. Do not assume the code is entirely self-documenting.
