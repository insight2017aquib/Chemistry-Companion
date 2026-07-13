# Mol* Visualization Integration

## Overview
The **Mol* (Molstar)** WebGL viewer is fully integrated into the Chemistry Companion's frontend `docking_workspace.html` layout. This serves as the visualization foundation for the Protein Preparation Workspace, Pocket Detection, Docking Visualization, and AI Protein Expert, enabling high-performance rendering without page refreshes.

## Key Capabilities

### 1. Zero-Refresh Rendering (Event Architecture)
- The Alpine.js state object (`dockingWorkspace()`) binds UI checkbox inputs (`showWaters`, `showMetals`, etc.) to a debounced `$watch` handler.
- When a toggle changes, Alpine commands the Mol* viewer to clear its existing scene and selectively rebuild the visual state without reloading the HTTP document. This provides a completely event-driven synchronization between the DOM and the WebGL canvas.

### 2. Live Visibility Toggles
Users have granular, instantaneous control over visualizing specific biological components identified by the Protein Analysis Engine:
- **Chains**: Isolate or combine specific chains (e.g., visualize only Chain A while hiding Chain B). Clicking a chain card triggers highlight, center, and updates.
- **Waters**: Toggle between all waters, active-site waters, bulk waters, or hide them entirely.
- **Metals**: Render and highlight catalytically significant transition metals (Zn, Mg, Fe, Mn, Cu, Ni, Co, Ca) alongside their coordinating residues.
- **Cofactors**: Render vital organic non-protein compounds (e.g., ATP, NAD, FAD, HEME).
- **Ligands**: Display bound native ligands.

### 3. Pocket & Gridbox Visualization
- **Pocket Highlighting**: Displays localized spheres or overlays emphasizing predicted pockets and experimental ligand sites. Clicking a pocket highlights it and updates metadata.
- **Gridbox Rendering**: Dynamically projects a translucent 3D box natively in Mol*. Users can show, hide, resize, and recenter the grid box instantly.

## Workspace State Persistence
The visualization layer is tightly coupled with the `WorkspaceManager`. The `exportLightweightState()` function continuously persists viewer settings to SQLite and the browser `localStorage`. 
The viewer state successfully survives:
- Module switching (navigating away and back)
- Browser refreshes
- Browser back button (`popstate` events)
- Workspace recovery from the database

## Architecture & Synchronization
- **Script Origin**: Mol* is dynamically loaded from the official CDN (`https://cdn.jsdelivr.net/npm/molstar@5.4.2/...`).
- **Viewer Component**: Initialized in `ensureMolstarViewer()`. Bound to the `#protein-preview-viewer` DOM host.
- **State Coupling**: 
  - `molstarRenderToken` acts as an async safeguard preventing stale render commands if the user rapidly toggles options.
  - Alpine strictly maintains the source of truth; Mol* operates as a pure-rendering visualizer downstream of `proteinAnalysis` and `grid` data.

---

## Visualization Wiring Audit (2026) — Live Protein Preview + Ligand 2D/3D

**Date**: Post-2026 session (wiring fixes applied)  
**Context**: User reported "GUI loaded but live structure preview of protein (Mol*) and 2D/3D ligand visualizations not happening". Full audit + surgical wiring performed per the approved plan in the session plan.md.

### Summary of Findings & Fixes (All Surgical, Full Reuse)
- **Simple ligand live 2D PNG preview** (`/api/structure.png` via `core/visualization_utils` + RDKit): The supporting `static/js/workbench.js` (commented "for dashboard + analysis") and the shared `components/molecule_input.html` ("Live preview" label) were only actually loaded on `spectra.html`. 
  - **Fix**: Made `workbench.js` defensive (tries `#input_text`/`#molecule-input` + `#structure-preview`), added global include from `base.html`. Now active wherever a compatible form + preview box exists. No new logic, no duplication.
- **Protein live Mol* preview** (docking_workspace.html sidebar): Fully wired (client-side PDB filtering + `loadStructureFromData`, live controls calling `renderProteinPreview`, restore paths already called it). 
  - **Issues addressed**: Timing/sizing after CDN create; error surfacing + console warn on failure. Two 1-2 line patches inside existing `ensureMolstarViewer` and `renderProteinPreview` catch.
  - The 2-column design (left controls, right persistent Mol* pane) and hybrid persistence (localStorage + WorkspaceManager) were already correct per `docs/developer/molstar_integration.md` and `protein_preparation_workspace.md`.
- **Advanced ligand 2D/3D + overlay** (`/api/visualization/{ligand2d,ligand3d,overlay}` + `visualization/` package guarded by `HAS_VISUALIZATION`): The endpoints, `VisualizationService`, renderers (delegating to core where possible), and frontend `render3DModels`/`ensure3Dmol` (3Dmol CDN) + `loadLigand` were already present and correctly mounted in `api/app.py`.
  - Minor observed inconsistency (server `.html` vs client mol_block) documented but left unchanged to avoid x-show side effects.
- **Health / Audit surface**: `/health` now includes `visualization.available` + message (extends existing health_check + VisualizationService). Existing `scripts/audit_*.py` + `tests/test_visualization_and_workspace_pages.py` reused as-is.
- **Dependencies**: Two stacks honored exactly (lightweight `core/visualization_utils` always-on; heavy `visualization/` + gemmi/rdkit/py3Dmol guarded). No new stacks created.

### Completed Audit Checklist (Key Items)
- [x] Mol* CDN loads + viewer created after Analyze Protein.
- [x] All Live Controls (waters, metals, cofactors, chains, pockets...) trigger instant filtered re-render.
- [x] Simple PNG preview now works on pages with the form elements (global wiring).
- [x] `/health` surfaces viz status.
- [x] 503 from viz endpoints remains actionable.
- [x] Existing tests (template strings + contracts) still pass.
- [ ] Full end-to-end on user's exact Windows launcher + browser (user to execute the matrix below and record results here).

### Recommended Manual Verification Matrix (Run on Actual Launcher)
1. Windows launcher → open dashboard or analysis → enter valid SMILES → PNG image appears in the preview area (or the box on spectra via the component).
2. Launcher → /docking-workspace → upload small .pdb → "Analyze Protein" → Mol* canvas appears in right pane with structure.
3. Toggle Live Controls (Show Waters, Show Metals, per-chain, etc.) → scene updates in < 2s, no page reload, camera preserved on most.
4. Prepare ligand in later step → ligand appears overlaid in the same Mol* viewer.
5. /visualization → enter ligand SMILES → 2D SVG renders + 3D canvas interactive.
6. Upload protein + render ligand → Overlay works.
7. Refresh / back-button / workspace restore → previews reappear.
8. (Optional negative) Simulate missing rdkit/gemmi → /health shows unavailable + 503s from /api/visualization/* are friendly.

**Windows/Conda Notes** (append here when discovered): rdkit and gemmi wheels can be sensitive to the exact conda python vs. pip. The project launchers and `conda_startup.log` already exist for this; prefer `conda install -c conda-forge rdkit gemmi` in the active env before `pip install -r requirements.txt`.

### Files Touched (All Minimal / Reusing Existing)
- `static/js/workbench.js`, `templates/base.html`, `templates/spectra.html` (Step 1)
- `templates/docking_workspace.html` (2 tiny patches, Step 2)
- `api/app.py` (1 import + 4-line health extension, Step 4)
- This doc + others in Step 6 (user-mandated)

**Zero duplication, full reuse** of `VisualizationService`, `core/visualization_utils`, existing Alpine methods, CDN loaders, WorkspaceManager persistence, audit scripts, and tests.

See the full session plan.md (and its "Architecture Alignment" section citing all the docs that were read before implementation) for constraints and rationale.

This section fulfills the 2026 user requirement to keep /docs updated for production and future scaling.
