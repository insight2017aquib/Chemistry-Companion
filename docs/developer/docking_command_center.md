# Docking Command Center (Phase 6)

## Overview
Phase 6 brings together all previously established foundations (Workspace Persistence, Mol* Visualization, Protein Analysis, AI Expert) into a professional, unified **Docking Command Center**. It establishes an end-to-end flow from PDB ingestion to deep interaction analysis.

## Core Components

### 1. Unified Docking Workspace (`docking_workspace.html`)
- **Integration**: Merges the Protein Preparation layout directly with AutoDock Vina configuration (Gridbox selection, Exhaustiveness, Modes).
- **Live State**: The Mol* viewer acts as the command center's eye, displaying the selected protein, active chain, isolated pockets, ligands, and a real-time rendering of the 3D gridbox coordinates.
- **Docking Execution**: Launches the asynchronous Vina pipeline, streaming standard output, elapsed time, and status back to the user without blocking the UI.

### 2. Docking Job Manager & History
- **Persistence**: All docking runs are persisted through `WorkspaceManager` to SQLite.
- **Job Recovery**: The system captures Queued, Running, Completed, and Failed states. Users can navigate back to previous jobs using the 'Recent Jobs Picker'.

### 3. Pose Viewer (`pose_analysis.html`)
- **Execution Handoff**: Once a Vina job completes, the workspace transitions to the Pose Analysis view.
- **Visual Mapping**: High-fidelity 3D rendering of the resulting docked ligand geometries, localized tightly within the receptor binding pocket.

### 4. Interaction Analysis (`interaction_analyzer.py`)
- **Algorithmic Detection**: Replaces heuristic guessing with strict geometric and chemical interaction mapping using RDKit (or OpenBabel as fallback).
- **Supported Interactions**:
  - Hydrogen Bonds (Distance/Angle constraints)
  - Hydrophobic Contacts
  - Salt Bridges (Charged centers)
  - Pi-Stacking
- **Results Table**: Displays calculated Binding Affinity (kcal/mol), RMSD boundaries, and detailed enumerations of non-covalent interactions for each ranked pose.

## Architecture
This Command Center completely decouples execution from the HTTP lifecycle. Vina runs as a background process, while Alpine.js polling updates the UI. The results are securely tethered to a `job_id`, ensuring the workflow is fully recoverable and meets the standards of professional medicinal chemistry pipelines.
