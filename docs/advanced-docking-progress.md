# Advanced Docking & Receptor Preparation — Progress Overview

**Last Updated**: 2026  
**Purpose**: Give both human developers and future AI agents a clear, high-level view of what has been built in the Advanced Docking Platform, especially around protein/receptor preparation.

## Overall Vision

Transform the Docking Workspace from a basic "upload → prepare → dock" tool into a **publication-grade, interactive, and scientifically trustworthy receptor preparation + docking platform**.

The goal is to support serious medicinal chemistry and virtual screening work while remaining accessible.

## Major Areas of Progress

### 1. Rich Receptor Analysis (Phase 1)

**Key Deliverable**: `ReceptorReport` + `analyze_receptor()` in `docking_workflow/protein_analysis.py`

**Capabilities**:
- Detailed per-chain breakdown
- Automatic classification of ligands, cofactors, and metals
- Extraction of resolution and experimental method (when available)
- Basic missing residue detection
- Quality scoring (0–100) with labels

**Entry Points**:
- `POST /api/docking/protein_analyze` (legacy, still supported)
- `POST /api/docking/receptor/analyze` (recommended rich version)

### 2. Binding Site Detection (Phase 3)

**A. Ligand-Based (3A)**
- When a co-crystallized ligand is present, the system computes:
  - Ligand centroid
  - Nearby protein residues
  - Recommended focused grid box
- Exposed via `/api/docking/receptor/ligand_sites`

**B. Pocket-Based (3B)**
- When no ligand is present, uses **fpocket** to predict binding pockets
- Returns ranked pockets with suggested grid boxes
- Exposed via `/api/docking/receptor/pockets`
- Graceful degradation if fpocket is not installed

### 3. Advanced Preparation Options (Phase 4 + 5)

**Key Deliverable**: `PreparationOptions` dataclass + `prepare_receptor()` in `docking_workflow/protein_preparation.py`

Supported controls:
- Remove waters (with smart active-site water retention)
- Add charges
- Selectively keep or remove cofactors
- Selectively keep or remove metals
- Run protonation at specific pH (Phase 7)

**Entry Point**: `POST /api/docking/protein_prepare` (now supports the full options set)

### 4. Water Analysis (Phase 6)

**Key Deliverable**: `docking_workflow/water_analysis.py`

- Classifies waters into `active_site` vs `bulk`
- Provides per-water `keep` / `remove` recommendations based on distance to binding sites
- Integrated into preparation when `keep_active_site_waters=True`

**Entry Point**: `POST /api/docking/receptor/waters`

### 5. Protonation Pipeline (Phase 7)

**Key Deliverable**: `docking_workflow/protonation.py`

- Optional pH-dependent protonation using **PDB2PQR + PropKa**
- Fully graceful: skips cleanly if the tool is not installed
- Can be used standalone or as part of full preparation

**Entry Points**:
- `POST /api/docking/receptor/protonate`
- Integrated into `prepare_receptor_with_options` via `run_protonation` + `ph`

### 6. Quality Scoring (Phase 8)

**Key Deliverable**: `docking_workflow/quality_scorer.py`

- Multi-factor 0–100 quality score + labels (`Excellent` / `Good` / `Acceptable` / `Poor`)
- Includes resolution, missing residues, ligand/pocket presence, cofactor/metal situation, and chain quality
- Detailed breakdown + notes for transparency

**Entry Point**: `POST /api/docking/receptor/quality`

## Current Architectural Strengths

- Strong separation: analysis → classification → preparation options → scoring
- Excellent use of `gemmi` for structure parsing
- All heavy scientific tools (fpocket, PDB2PQR) are optional with clear degradation
- Rich data models (`ReceptorReport`, `PreparationOptions`, `BindingSiteSuggestion`, `Pocket`, `WaterInfo`, etc.)
- Good API surface with both legacy and new rich endpoints

## Known Gaps / Next Focus Areas (as of this document)

- **Live 3D preview during preparation** (current active plan — see `docs/docking-preparation-live-preview.md`)
- Session state resilience in the preparation wizard
- Easy download of prepared receptors
- Better persistence of preparation decisions into job reports
- Further strengthening of quality scoring and water classification heuristics

## Recommended Reading Order (for context)

1. `docs/ADVANCED_DOCKING_PLAN.md` — Original master vision
2. `docs/docking-preparation-live-preview.md` — Current active workstream (live visualization + resilience)
3. `docs/advanced-docking-progress.md` — This file (high-level summary)
4. Individual module docstrings in `docking_workflow/`

## For Future AI Agents

When resuming work on this project:

- Always read the three documents above first.
- The most up-to-date user priorities are usually in the active session plan + the `docking-preparation-live-preview.md` file.
- The backend is now quite mature for receptor preparation. Most remaining high-value work is in **interactivity**, **state management**, **visualization**, and **polish** rather than new scientific algorithms.

---

**Document maintained for long-term context and reproducibility.**