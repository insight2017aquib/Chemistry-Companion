# Protein Preparation Workspace (Phase 4)

## Overview
The Protein Preparation Workspace transforms the underlying scientific capabilities of the Protein Analysis Engine and the Mol* Visualization Layer into a cohesive, interactive user experience. It is seamlessly integrated into the initial steps (Steps 1–3) of the `docking_workspace.html` wizard, fulfilling the requirement for a robust workstation without breaking the continuous docking workflow.

## Layout & Architecture
Rather than a rigid 3-panel layout, the workspace employs a responsive **2-column split layout** (`lg:grid-cols-12`):
- **Main Interaction Area (`lg:col-span-8`)**: Houses the Protein Summary, Interactive Chain Cards, Pocket Cards, Water/Cofactor/Metal summaries, and Preparation Option toggles.
- **Persistent Live Preview (`lg:col-span-4`)**: The Mol* WebGL Viewer stays anchored on the right side, instantly reflecting any changes made in the main interaction area.

## Supported Workflows

### 1. Chain & Pocket Workflow
- **Interactive Cards**: Renders cards for each detected chain and pocket.
- **Metadata Display**: Shows residue counts, ligands, completeness, and quality scores.
- **Action**: Clicking a chain or pocket triggers `renderProteinPreview()` which highlights and centers the Mol* viewer on the target without refreshing the page.

### 2. Water, Metal, & Cofactor Workflow
- **Display**: Lists active-site vs. bulk waters, catalytic vs. artifact metals, and required vs. optional cofactors.
- **Controls**: Granular UI toggles to "Keep Active-Site Waters", "Remove Bulk Waters", "Keep Metals", and "Keep Cofactors".
- **Preview**: Interacts cleanly with Alpine.js to update visibility dynamically in the Mol* panel.

### 3. Preparation Options & Receptor Generation
- **Protonation & Charges**: The "Add Gasteiger charges & polar hydrogens" option acts as the primary protonation/charge repair mechanism before conversion.
- **Output**: The workflow culminates in generating the final `.pdbqt` receptor payload. The user can preview this output directly in the UI before proceeding to docking.

## Workspace Integration
The entire preparation state is coupled to the `WorkspaceManager`. Toggles, selected chains, and gridbox coordinates are persisted in real-time via `exportLightweightState()` to both `localStorage` and the SQLite database. This ensures the preparation session survives browser navigation, refreshes, and project switching.
