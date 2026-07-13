# Plan: Advanced Docking Platform for Chemistry Companion

> **How to save/download this plan locally**  
> The live plan file is here (copy this entire path):  
> `\\?\C:\Users\Aquib Belal\.grok\sessions\C%3A%5CWindows%5CSystem32\019e7425-4b79-7dd3-84b3-cfab7d6df69c\plan.md`  
> 
> **Easiest ways**:
> 1. Open the path above in VS Code / Notepad++ / any editor and **File → Save As** into your project:  
>    `C:\Users\Aquib Belal\Documents\Chemistry Companion\docs\ADVANCED_DOCKING_PLAN.md` (create the `docs/` folder if needed).
> 2. Or ask me "print the full plan" and copy-paste the output into a new file in your project.
> 3. Once saved locally, you can edit it directly and we can sync changes back here if needed.

**Date**: 2026 (current session)  
**Project Root**: `C:\Users\Aquib Belal\Documents\Chemistry Companion`  
**Goal**: Transform the existing functional docking workspace into a production-grade, research-ready **Advanced Docking Platform** integrated deeply into Chemistry Companion.

---

## Context

Chemistry Companion already contains a substantial docking foundation (developed by the user):

- **docking_workflow/** package with Vina subprocess runner, protein prep (OpenBabel + rigid receptor cleaning), auto gridbox, pose parser, basic report builder.
- **DockingWorkspaceService** + FastAPI routes (`/api/docking/*`) powering a polished 4-step Alpine.js wizard at `/docking-workspace`.
- Legacy ligand-only prep at `/docking`.
- Pose analysis page at `/pose-analysis` with 3Dmol.js viewer + HTMX-powered LLM explanations (multi-provider with rich fallbacks in `core/llm_utils.py`).
- Visualization module (`visualization/`, `/api/visualization/overlay`) for protein-ligand complexes.
- File-based job persistence in `outputs/docking_workspace/<job_id>/` (protein.pdbqt, vina_out.pdbqt, report.json, per-pose SDFs, logs).
- Strong surrounding infrastructure: DB-backed history (AnalysisResult), exports, LLM, batch patterns, optional-dep guards (`HAS_DOCKING`).

**Current limitations blocking "advanced" status**:
- `interaction_mapper.py` is a pure placeholder returning hardcoded mock interactions.
- `pose_analysis.html` uses hardcoded sample data; it is **not connected** to real docking job IDs or the workspace service.
- No DB model or history integration for docking sessions (only ephemeral filesystem folders).
- Visualization is basic sticks; no interaction geometry (H-bonds as lines), no surfaces, no 2D interaction diagrams (LigPlot-style), no pocket highlighting.
- Single-ligand only. No virtual screening / multi-ligand batching inside the workspace.
- Limited binding site definition (numeric box only; no residue picker or reference ligand mode).
- No job reload/compare, no professional exports (PyMOL sessions, publication figures, full PDF reports with viz).
- No use yet of vendored meeko or advanced Vina 1.2+ features (flexible sidechains).
- UX is wizard-linear; lacks project/session management feel of a real platform.

The user wants to evolve this into an **advanced docking platform** — a first-class, visually rich, scientifically credible module comparable in depth to the existing spectra + analysis pipelines.

---

## Recommended Approach

**Phased, high-signal incremental delivery** (avoid big-bang rewrite). Leverage every existing pattern.

### Core Phases (Docking Platform)
1. **Foundation (highest ROI)**: Real interaction detection + make pose analysis a real, job-aware page + add minimal DB persistence for docking sessions.
2. **Visualization & Scientific Depth**: Upgrade 3D + add 2D interaction diagrams; improve gridbox UX with residue awareness. **This is where Chimera/ChimeraX integration lives** (see dedicated section below).
3. **Power User Features**: Multi-ligand screening mode, flexible receptor support (meeko), advanced prep options, rich exports + reports.
4. **Polish & Platformization**: Session browser, comparison tools, reproducibility artifacts, tighter LLM + history integration.

**Key principles**:
- Keep `HAS_DOCKING` guard + graceful degradation everywhere.
- Prefer pure-Python + existing deps (RDKit + OpenBabel + gemmi) for interactions before heavy libs.
- Extend, do not replace existing flows.
- File workspaces = artifact source of truth; DB for fast metadata/history.
- All new endpoints follow existing router + Pydantic + service layer shape.

**Trade-offs**:
- Phased over big-bang.
- Self-contained first, then excellent bridges to power tools (especially ChimeraX).

---

## Chimera & ChimeraX Visualization Integration (Key Enhancement)

**Why this matters for "advanced docking platform" + "very interactive GUI"**:
- UCSF Chimera / ChimeraX are the gold standard for interactive molecular visualization in computational chemistry and structural biology.
- Current Chemistry Companion uses 3Dmol.js (lightweight, zero-install, browser-only). Excellent for quick web use, but limited rendering quality, no native session persistence, weaker measurement/analysis tools, and no ray-tracing or publication movie capabilities.
- Users doing serious docking (especially the author of this project) almost always end up opening results in Chimera/ChimeraX anyway. Making this **first-class and seamless** turns Chemistry Companion from "nice web tool" into a true **integrated docking workstation**.

### Vision for Very Interactive GUI + Chimera
- **Primary web GUI** (Alpine + 3Dmol.js + custom controls) stays fast and zero-install:
  - Residue/atom picking in the 3D view that highlights rows in the interaction table and vice-versa (true bidirectional selection, very Chimera-like).
  - On-the-fly style changes (cartoon/surface/stick, color by b-factor or by interaction type).
  - Distance/angle measurement tools that update live.
  - "Focus on pocket" / "hide non-interacting residues" buttons that feel native.
- **Power-user escape hatch — "Open in ChimeraX"** (one prominent button on every pose and on the workspace results):
  - Generates a complete, ready-to-run ChimeraX script (`.cxc`) + all necessary structure files (receptor PDBQT/PDB + selected pose SDF/PDBQT).
  - The script automatically:
    - Loads the exact complex from the job workspace.
    - Applies beautiful publication-quality styling (transparent surface on protein, green sticks for ligand, dashed H-bonds, labeled interacting residues, etc.).
    - Runs any available ChimeraX interaction analysis (HBonds tool, etc.).
    - Sets up a nice preset view (often better than anything web can do).
  - Optionally launches ChimeraX directly from the GUI if the executable is configured in settings (cross-platform, with good error messages).
- **Live / bidirectional control (advanced, very interactive)**:
  - If the user has ChimeraX running with its REST interface enabled (`chimerax --enable-remote`), the web app can send live commands (change representation, color specific residues, save image, run `hbonds`, take snapshot).
  - This gives the "very interactive GUI" feeling: use the friendly web wizard and tables to drive a full ChimeraX session.
- **High-quality exports**:
  - Ray-traced PNGs (ChimeraX `save` with high resolution + lighting).
  - Animation movies of pose morphing or fly-throughs.
  - Full ChimeraX session files (`.cxs`) that the user can save and reopen later with every view/state preserved.

### Implementation Notes (stay lightweight)
- Do **not** bundle ChimeraX (it's huge and platform-specific). Treat it exactly like the existing Vina binary: discover via PATH or user-configured setting (`CHIMERA_EXECUTABLE` or `CHIMERAX_EXECUTABLE`).
- New small module: `docking_workflow/chimera_exporter.py` (or `exports/chimera/`) that knows how to write excellent `.cxc` scripts using the same job artifacts already on disk.
- New service methods + 2–3 API endpoints: `POST /api/docking/{job_id}/chimera_script`, `POST /api/docking/{job_id}/open_in_chimera` (best-effort launch).
- Settings page gets a new "External Tools" section (already has LLM provider switching — follow the same pattern).
- Graceful: if ChimeraX not found, the button still downloads the perfect `.cxc` + files bundle (user can double-click the script on their machine).
- Leverage existing `visualization/complex_renderer.py` as the web-side complement.

This combination (rich web picking/measurement GUI + instant professional ChimeraX session) is exactly what makes a docking platform feel "advanced" and truly interactive to working scientists.

---

## Trade-offs Specific to Chimera Integration

- Full embedded ChimeraX (impossible in web) vs script + optional launch: **script + optional launch wins** (matches how the project already handles vina binary).
- Always require ChimeraX vs optional power feature: **optional** — the web experience must remain excellent and self-contained.

---

## Critical Files & Existing Code to Reuse

### Must Modify / Extend
| File | Purpose | Existing Code to Leverage |
|------|---------|---------------------------|
| `docking_workflow/interaction_mapper.py` | Replace mock with real geometry-based detection | Current `Interaction` dataclass + `map_interactions` signature |
| `docking_workflow/interaction_analyzer.py` (new) | Dedicated, testable module for H-bonds, hydrophobics, pi-stacking, salt bridges using RDKit/OpenBabel distances + angles | `pose_manager.DockingPose`, protein/ligand PDBQT parsers already in workspace |
| `docking_workflow/chimera_exporter.py` (new) or `exports/chimera/` | Generate excellent `.cxc` scripts + file bundles; optional direct ChimeraX launch for "very interactive" pro viz | Existing job workspace artifacts (protein.pdbqt, pose_*.sdf, report.json), `visualization/complex_renderer.py` patterns |
| `database/models.py` | Add `DockingJob` / `DockingSession` model (job_id, receptor_name, ligand_smiles, grid, scores, created_at, tags, paths) | Pattern from `AnalysisResult` + `BatchJob` |
| `services/docking_workspace_service.py` | Add `list_jobs()`, `load_job()`, `save_job_metadata()`, `run_batch_docking()`, Chimera script/launch helpers | Current `get_workspace`, `run_docking`, file I/O helpers, `HAS_DOCKING` checks |
| `api/routes/docking_workspace.py` | New endpoints: `GET /jobs`, `POST /job/{id}/load`, batch run, interactions, **Chimera script + launch** | Current router shape + `_require_docking()` guard + Pydantic models |
| `templates/pose_analysis.html` | Make fully dynamic (job_id driven, real data) **+ rich interactive picking/measurements + prominent "Open in ChimeraX" button** | Current Alpine `poseAnalysis()`, HTMX LLM form, 3Dmol fallback logic, `/api/visualization/overlay` |
| `templates/docking_workspace.html` | Add history/save/load + "Open in ChimeraX" on results | Current 4-step wizard + Alpine state |
| `templates/components/` | New: `docking_poses_table.html`, `interaction_list.html`, `gridbox_editor.html`, `docking_job_card.html`, `chimera_launcher.html` | Existing component patterns (e.g. `descriptors_panel.html`) |
| `api/schemas/` (extend or new `docking.py`) | Pydantic models for job summaries, batch requests, chimera responses | Pattern from `api/schemas/*.py` |
| `visualization/` (extend) | 2D interaction diagrams + enhanced complex viz; helpers for Chimera-friendly exports | `complex_renderer.py`, `viewer_service.py`, `VisualizationOrchestrator` |
| `core/models.py` | Optional: `DockingPoseRecord`, `DockingResult` dataclasses | `ModelMixin` + existing dataclass patterns |
| `reports/export_utils.py` + docking report builder | Multi-format exports including **ChimeraX bundles** + PyMOL scripts | Current `reports/`, `exports/excel/`, `services/excel_report_service.py` |
| `llm/docking_explainer.py` + `core/llm_utils.py` | Minor hardening if needed | Already excellent multi-layer fallback |
| `templates/settings.html` + related | New "External Tools" section for ChimeraX executable path (mirror LLM provider UI) | Current settings + LLM switching code |

### Read-Only / Reference (Strong Patterns)
- `docking_workflow/vina_runner.py`, `protein_preparation.py`, `pose_manager.py`, `gridbox_builder.py` — do not change core unless needed for new options.
- `services/visualization_service.py`
- `api/app.py` (mounting + page routes) — just add any new pages.
- `core/openbabel_utils.py`, `core/docking_preparation.py`
- `tests/test_docking_*.py` + general test patterns
- `static/js/` (minimal; most logic lives in templates today)

### New Directories / Files (Minimal)
- `outputs/docking_workspace/` already exists (keep structure).
- Possibly `docking_workspace/` enhancements stay in existing package.
- New test files under `tests/` following naming (`test_docking_interactions.py`, `test_docking_persistence.py`).

---

## Detailed Implementation Phases (for Execution)

### Phase 1a (Completed 2026): Pre-Docking Chain Identification & Chimera-style Inspection
- Full implementation of protein chain detection, per-chain stats, intelligent recommendation, and user selection **before** preparation/docking.
- New module: `docking_workflow/protein_analysis.py`
- New endpoint: `POST /api/docking/protein_analyze`
- Rich UI panel inside the existing Docking Workspace Step 1 + automatic filtering on Prepare.
- Selected chains + analysis summary are persisted in the job `report.json`.
- See the dedicated session plan for this vertical: `~/.grok/sessions/.../plan.md`

### Phase 1b: Real Interactions + Job-Aware Pose Analysis (Foundation) — Completed 2026
- Real `interaction_analyzer.py` (H-bonds, hydrophobics, etc. with proper geometry).
- **Pose Analysis page hardened**: `pose_analysis.html` is now **strictly real-job only**. No more hardcoded demo data (Aspirin poses/interactions/ligand). 
  - Honest professional empty state when visited without `?job_id`.
  - "Browse My Recent Docking Jobs" picker using existing `/api/docking/jobs`.
  - SessionStorage handoff resilience for back/refresh/navigation.
- `DockingJob` DB model + basic save/reload/history wiring (already present).
- Tests remain green.

**Major UX win**: A user who completes a real docking job now sees *only* their data on the Pose Analysis page. No more convincing fake results.

### Phase 1c: AI Expert Chain Recommendation (25-year docking scientist) — Completed 2026
- New capability: "Ask the docking expert" for intelligent chain selection on multi-chain proteins (directly addresses real-world failures like 4duh where pure heuristics pick the wrong chain).
- New service method + high-quality expert prompt in `services/docking_workspace_service.py` (written from the perspective of a 25-year veteran who has led 40+ programs).
  - Prompt asks for binding site location, catalytic residues, biological assembly considerations, why other chains are less relevant, red flags, etc.
  - Returns structured JSON: `recommended_chain_ids`, `confidence`, rich `rationale`, `warnings`.
  - Robust parsing + graceful fallback to the existing heuristic.
- New endpoint: `POST /api/docking/ai_chain_recommendation`.
- Fully integrated UI in Docking Workspace Step 1 "Protein Structure Analysis" panel:
  - Keeps the fast heuristic recommendation (now labeled as such).
  - New "🧠 Ask AI Docking Expert" button.
  - Distinct AI card with confidence, expandable scientific rationale, and prominent "Use AI Recommendation" button.
  - Choice (heuristic vs AI) + full rationale persisted in the job report under `protein_preparation.analysis`.
- When ligand SMILES is already known, it is passed to the AI for higher-quality context.

**Deliverable**: On real drug discovery targets, the user gets expert-grade chain reasoning they can defend in a project meeting, not just "biggest chain with a ligand". The system now feels like having a senior docking scientist as a collaborator inside the wizard.

**Tests & verification**: Existing docking tests green. Lightweight mocked test for the new AI path added. Full golden-path verification (multi-chain PDB → AI rec → Prepare → real Pose Analysis with only real data) is the responsibility of the user running the app with real structures.

### Phase 2: Very Interactive GUI + ChimeraX Integration (the star feature for advanced platform)
**Web GUI (feels Chimera-like inside the browser)**:
- Bidirectional picking: click residue/atom in 3Dmol view → instantly highlights the corresponding row in the interaction/pose tables (and vice-versa).
- Live measurement tools, surface toggles, "focus pocket", "hide everything except interacting residues".
- 2D interaction diagrams (LigPlot style).

**ChimeraX power bridge (what actually makes it feel advanced to scientists)**:
- New `chimera_exporter.py`: produces beautiful, publication-ready `.cxc` scripts + complete self-contained file bundles from any docking job.
- Big, obvious **"Open in ChimeraX"** button on workspace results and every pose.
  - Downloads the perfect script + structures.
  - If user has configured ChimeraX path in Settings → also offers one-click launch.
- Optional live control: when ChimeraX REST is enabled, the web GUI can drive it (change styles, run `hbonds`, save ray-traced images, etc.).
- High-end exports: ray-traced PNGs and even short movies generated via ChimeraX when available.

**Also in this phase**:
- Residue-aware gridbox definition.
- Reusable UI components.

**Deliverable**: The web experience is already highly interactive. One click gives the user a full professional ChimeraX session of their exact docked complex with gorgeous rendering and all the analysis tools they expect.

### Phase 3: Screening & Advanced Docking Capabilities
- Multi-ligand virtual screening mode against one receptor.
- Flexible side-chain support (meeko).
- Full reproducibility metadata (exact Vina command, versions, seed).

### Phase 4: Platform & Professional Reporting
- Dedicated docking sessions history / browser.
- "Publication Bundle" export that includes the ChimeraX script + optionally high-quality images rendered through ChimeraX.
- Update all docs (limitations, roadmap, README).
- Validation of the interaction analyzer.

---

## Verification Strategy (End-to-End)

**Core checks after each phase**:
- Unit tests for new interaction code + full job persistence roundtrips. Old docking tests stay green.
- End-to-end API + UI: real docking run → pose analysis page (with real data + real interactions) → working LLM explanation.
- **Golden interactive flow**:
  1. Run a docking job in the workspace.
  2. Go to pose analysis → verify rich picking/selection sync between 3D view and tables (very Chimera-like).
  3. Click "Open in ChimeraX" → either get a perfect ready-to-run script+files, or (if configured) ChimeraX actually launches with the beautiful pre-styled session.
  4. "Save to History" works and the session is reloadable later.
- Graceful degradation: everything works (with clear messaging) when ChimeraX or vina deps are absent.
- Reproducibility of Vina results + ChimeraX scripts are deterministic for the same job.

Keep verification focused on vertical user stories rather than 100% coverage.

---

## Open Questions (Chimera-specific ones highlighted)
- Priority: Phase 1 (real interactions + job-aware analysis) first, or do you want ChimeraX export in the very first slice?
- For the "very interactive GUI": how important is live bidirectional picking vs great static viz + one-click ChimeraX?
- Do you already have ChimeraX installed? Preferred way to discover it (PATH, explicit setting in Settings page, or both)?
- Should we support classic Chimera (the older one) as well as ChimeraX, or ChimeraX only?
- For live REST control of ChimeraX — nice-to-have later, or important for v1 of the interactive experience?
- Any specific ChimeraX presets/styles/commands you love for docked complexes (e.g. particular surface transparency + H-bond style + label scheme)?

---

## Success Metrics

- A user can go from "I have a PDB + SMILES" → "I have ranked poses + real interactions + AI explanation + publication-ready artifacts" in < 10 minutes with zero command line.
- All existing docking functionality continues to work unchanged.
- New interaction code is unit-tested and produces chemically plausible output on real systems.
- Pose analysis page is now the primary post-docking destination and feels "advanced".
- Docking sessions become first-class citizens in the app's history and data model.

This plan is scoped to be ambitious yet executable in clear vertical slices while maximally reusing the excellent foundation already present in the Chemistry Companion codebase.
