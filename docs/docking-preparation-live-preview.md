# Docking Workspace: Live Protein Preparation + Session Resilience + Download

**Status**: Approved (2026)  
**Owner**: Advanced Docking Platform initiative  
**Related Plan**: See the session plan at `~/.grok/sessions/.../plan.md` (session 019e78eb-...)

## Goal

Make Step 1 ("Upload & Prepare Protein") in the Docking Workspace a true **interactive, trustworthy preparation workstation** instead of a black-box "upload → prepare → hope" flow.

### Specific User Requirements

- **Live 3D Visualization**: When the user toggles any preparation option (Remove Waters, Add Charges, Keep Cofactors, Keep Metals, Run Protonation, pH value, etc.), the 3D structure must update **in real time** so the effect is immediately visible.
- **Session Resilience**: The entire preparation state (uploaded PDB, selected chains, all options) must survive browser refresh, back/forward navigation, or tab close. Currently the state is lost.
- **Download Prepared Protein**: Users must be able to download the final prepared `.pdbqt` file easily at any point.

## Background & Motivation

The project has already invested heavily in advanced receptor preparation capabilities:

- Rich `ReceptorReport` with ligand/cofactor/metal classification (Phase 1)
- Ligand-based and pocket-based binding site detection (Phase 3A + 3B)
- Selective cofactor and metal retention during preparation (Phase 4+5)
- Smart water classification with keep/remove recommendations (Phase 6)
- Optional protonation via PDB2PQR + PropKa (Phase 7)
- Multi-factor quality scoring (Phase 8)

However, the **user experience** of the preparation step itself remained traditional:
- Options are set → "Prepare Protein" button is clicked → result appears later.
- No visual feedback during option changes.
- State is ephemeral (Alpine.js only).
- No easy way to export the prepared receptor independently.

This plan closes that gap and turns the preparation step into a first-class, highly interactive experience.

## Proposed Solution

### 1. Live Preview System

**Backend**
- New endpoint: `POST /api/docking/protein_preview`
- Accepts current PDB text + all preparation options.
- Returns the prepared PDBQT (or a lightweight preview version).
- Performance strategy:
  - Client-side water stripping for instant feedback on water removal.
  - Server round-trips only for expensive operations (charges, protonation).

**Frontend (Step 1)**
- Embed a 3Dmol.js viewer directly in the preparation form.
- On option change (debounced), trigger preview and update the viewer.
- Clear visual feedback ("Preparing preview…").

### 2. Session State Persistence

Persist the entire Step 1 state using `sessionStorage`:

- Original PDB content (base64)
- Selected chains
- All preparation toggles (`removeWater`, `addCharges`, `keepCofactors`, `keepMetals`, `runProtonation`, `ph`)
- Prepared PDBQT (when available)

On reload:
- Automatically restore the previous state.
- Show a non-intrusive "Restored previous preparation session" banner with a "Clear" button.

This directly solves the "session gets lost" pain.

### 3. Download Capability

- Prominent **"Download Prepared PDBQT"** button appears after any successful preparation (or preview).
- Standard Blob download with sensible filename (e.g. `prepared_4duh_ph7.4.pdbqt`).
- Available even before moving to the next wizard step.

## Implementation Priorities (Recommended Order)

1. Backend preview endpoint + service method (`/protein_preview`)
2. SessionStorage save/restore logic (highest immediate value for preventing data loss)
3. Download button for prepared PDBQT
4. Live 3Dmol viewer integration in Step 1 + option change wiring
5. Polish (debouncing, loading states, better error handling, "Clear session" UX)

## Risks & Mitigations

- **Performance** on large structures when toggling options frequently → Use debouncing + client-side fast paths for water removal.
- **sessionStorage size limits** with large PDB files → Store only the original PDB + options; re-prepare on restore when necessary. Show clear warnings for very large files.
- **3Dmol re-rendering cost** → Prefer model replacement APIs over full viewer re-initialization when possible.

## Success Criteria

- Toggling preparation options produces visible 3D updates in < 1s (water removal) or a few seconds (full prep).
- Refreshing the page or using browser navigation in Step 1 restores the exact previous state.
- User can download the prepared `.pdbqt` with one click after preparation.
- No accidental loss of work during the preparation phase.

## Related Documentation

- Master Advanced Docking Plan: `docs/ADVANCED_DOCKING_PLAN.md`
- Current session plan (detailed implementation): See the active session plan file for this conversation.

---

**Last Updated**: 2026 (after plan approval)  
**Next Action**: Begin implementation starting with the preview endpoint + session persistence (highest risk / highest value items).