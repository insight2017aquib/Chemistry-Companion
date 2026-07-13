# PHASE_03_VISUALIZATION.md

OBJECTIVE

Create a modern protein preparation workspace with live visualization.

TASKS

## Mol* Integration

Integrate Mol* Viewer.

Requirements:

* Protein rendering
* Ligand rendering
* Metal rendering
* Pocket rendering
* Gridbox rendering

No page refreshes.

---

## Live Controls

Implement:

* Show Waters
* Show Active-Site Waters
* Show Bulk Waters
* Show Metals
* Show Cofactors
* Show Ligands
* Show Chain A
* Show Chain B
* Show Chain C
* Show Pockets
* Show Grid Box
* Show Missing Residues

---

## Interactive Events

When user toggles waters:

waters disappear instantly.

When user toggles chain:

chain disappears instantly.

When user selects pocket:

highlight pocket instantly.

---

## Docking Workspace Redesign

Wizard:

STEP 1
Upload Protein

STEP 2
Protein Analysis

STEP 3
Chain Selection

STEP 4
Pocket Selection

STEP 5
Preparation Options

STEP 6
Generate Receptor

STEP 7
Docking

---

## UI Components

Recommendation cards

Confidence indicators

Quality badges

Pocket cards

Metal cards

Water cards

Cofactor cards

---

DELIVERABLES

Fully working Mol* Viewer

Live visualization

Frontend redesign

Documentation

Tests

---

## Implementation Notes

Status: implemented in `templates/docking_workspace.html`.

The docking workspace now uses a seven-step wizard:

1. Upload Protein
2. Protein Analysis
3. Chain Selection
4. Pocket Selection
5. Preparation Options
6. Generate Receptor
7. Docking

The live preview is powered by Mol* Viewer from the pinned CDN bundle
`molstar@5.4.2`. Structures are loaded without page refreshes through
`molstar.Viewer.create(...)` and `viewer.loadStructureFromData(...)`.

Live controls include waters, active-site waters, bulk waters, metals,
cofactors, ligands, per-chain visibility, pockets, grid box, and missing
residues. Protein/chain/water/metal/cofactor/ligand visibility is applied by
filtering the in-memory PDB text and reloading the Mol* scene. Pocket selection
updates the grid box, shows the pocket overlay, and asks Mol* to select/focus
nearby residues when residue annotations are available.

The UI includes recommendation cards, confidence indicators, quality badges,
pocket cards, metal cards, water cards, and cofactor cards. Receptor generation
still uses the existing `/api/docking/protein_prepare` backend, while analysis,
pocket, and water data come from:

* `/api/docking/receptor/analyze`
* `/api/docking/receptor/ligand_sites`
* `/api/docking/receptor/pockets`
* `/api/docking/receptor/waters`

Regression coverage:

* `tests/test_visualization_and_workspace_pages.py`
* `tests/test_api_docking_workspace_protein_endpoints.py`

**2026 Wiring Audit Note**: See `docs/developer/molstar_integration.md` → "Visualization Wiring Audit (2026)" section for the post-implementation state of live Mol* protein preview + ligand 2D/3D (simple PNG globally wired via workbench.js + base.html; Mol* hardened with 2 surgical patches; health surface extended; full reuse of existing stacks and no new duplication). All changes were append/surgical per DEVELOPMENT_RULES.md.
