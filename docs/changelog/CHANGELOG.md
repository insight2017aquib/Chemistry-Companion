# Changelog

## [Unreleased]

### Added — Phase 02 Protein Analysis Layer (2026-05-31)
- **Chain Analysis**: Added detection for residue count, missing residues, ligands, cofactors, metals, and waters, along with chain scoring and recommendations.
- **Water Analysis**: Added classification for active-site, conserved, and bulk waters with recommendations.
- **Cofactor Analysis**: Added detection and classification (Required, Optional, Artifact) for common cofactors (ATP, ADP, NAD, etc.).
- **Metal Analysis**: Added detection for common metals (Zn, Mg, Fe, etc.) with coordinating residues and catalytic relevance.
- **Quality Assessment**: Added 0-100 scoring based on resolution, missing residues, active-site integrity, and chain completeness.
- **Missing Residues**: Integrated REMARK 465 detection and reporting.
- **Protonation Framework**: Integrated PDB2PQR and PropKa support in the backend.
- **API Endpoints**: Deployed `/protein/analyze`, `/protein/chains`, `/protein/waters`, `/protein/cofactors`, `/protein/metals`, and `/protein/quality` endpoints.
- **Tests**: Implemented complete test coverage for new protein analysis features (`tests/test_api_docking_workspace_protein_endpoints.py`).
### Added — Phase 01 Foundation (2026-05-31)
- **Documentation Framework**: `docs/architecture/system_overview.md` with Mermaid diagrams, `ARCHITECTURE_DECISIONS.md` with ADR template, `DEVELOPER_GUIDE.md`, `PHASE_STATUS.md`
- **AI Provider Manager**: `services/ai/provider_manager.py` — unified facade over `core/llm_utils.py` with Gemini support, health checks, structured JSON responses
- **Gemini Provider**: Added Google Gemini to `core/llm_utils.py` provider registry (REST API, no SDK dependency)
- **AI Recommendation Framework**: `services/ai/recommendations.py` — interfaces for `recommend_chain`, `recommend_pocket`, `recommend_waters`, `recommend_cofactors`, `recommend_metals`
- **Tests**: `test_ai_provider_manager.py`, `test_ai_recommendations.py`
- **Protein Analysis API**: Added rich `/api/docking/protein/*` endpoints for analysis, chain summaries, waters, cofactors, metals, and quality scoring.
- **Environment Variables**: `GROQ_API_KEY`, `GEMINI_API_KEY`, `DEFAULT_FAST_PROVIDER`, `DEFAULT_REASONING_PROVIDER`, `FALLBACK_CHAIN`
- **Docking Workspace Enhancements**: `api/routes/docking_workspace.py` adds advanced protein preparation options, protonation controls, chain selection metadata, and richer docking run payloads; `services/docking_workspace_service.py` and `database/models.py` support enhanced job persistence and workflow metadata.
- **LLM Explanation & Provider Management**: `api/routes/llm_explanation.py` now exposes provider listing, active provider status, runtime provider switching, and the `core/llm_utils.py` explanation engine.
- **Docking UI Updates**: updated `templates/docking_workspace.html`, `templates/pose_analysis.html`, and `templates/settings.html` to support the new workspace controls, analysis metadata, and provider selection features.
- **Workflow and Schema Improvements**: `api/schemas/__init__.py`, `docking_workflow/interaction_mapper.py`, `docking_workflow/protein_preparation.py`, and `core/config.py` were updated for improved protein analysis, receptor preparation, and docking workflow support.
- **Benchmark Data Added**: added `data/benchmark_molecules.csv` and `data/spectra_benchmark.csv` for validation and testing.
