# Phase 1: Workspace Persistence

## Goal
Implement a project-level workspace persistence model to prevent data loss during long-running tasks, browser refreshes, or navigation changes. This replaces temporary HTTP sessions with durable project entities.

## Architecture

We implemented a **Hybrid Storage Model**:
- **SQLite Database (`Workspace` model):** Stores lightweight state, UI configurations, selected step, active tabs, viewer toggles, and metadata.
- **File System (`outputs/workspaces/{id}/`):** Stores heavy blobs such as the original parsed PDB text, PDBQT output buffers, and complex analysis arrays to avoid bloating the database row size limit.

## Key Features

1. **Auto-Save (Debounced):** 
   - Uses an Alpine.js `$watch` system tracking all major variables (`step`, `grid`, `showWaters`, etc.). 
   - Changes trigger an API `PUT` to the backend after 2 seconds of inactivity.
2. **Immediate Local Cache (`localStorage`):** 
   - Client-side cache acts as an immediate fallback, saving state synchronously so that even sudden crashes or network drops don't lose the immediate change.
3. **Auto-Recovery:**
   - URLs automatically push `?workspace_id=wksp_1234` when the user works. 
   - Reopening this URL pulls the heavy state back into the UI automatically.
   - If a new un-ID'd session was crashed, it looks up `localStorage` and asks to recover the state.
4. **Browser History Tracking:**
   - Wizard steps are mapped to `history.pushState`. The user can press the browser "Back" button to return to Step 1 from Step 2 without losing state.
5. **Viewer-State Persistence:**
   - Mol* WebGL viewer checkboxes (show bulk waters, show metals) and current camera states are saved so the view exactly matches the user's last session upon recovery.

## Status
- **Implementation:** Completed
- **Dependencies:** None
- **Next Phase:** Proceeding to specific docking improvements or visualizations.
