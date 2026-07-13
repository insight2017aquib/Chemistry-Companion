# Virtual Screening Architecture (Phase 8 Design)

## Executive Summary
This document outlines the architecture for the Phase 8 Virtual Screening module. The primary goal is to enable high-throughput docking of ligand libraries (SDF/CSV) against a prepared receptor while strictly avoiding technical debt. This is achieved by deeply reusing the existing Phase 1-7 infrastructure (WorkspaceManager, Protein/Ligand Preparation, Interaction Analyzer, and AI Expert) rather than building isolated, duplicative workflows.

## 1. Core Principles
1. **Zero Preparation Duplication**: Virtual Screening (VS) jobs will NOT implement their own protein preparation logic. They will strictly require a pre-prepared receptor loaded from an existing `Workspace`.
2. **Modular Execution**: The underlying Vina execution must reuse the core `docking_workflow` primitives, simply wrapping them in an asynchronous, concurrency-limited batch runner.
3. **Database-Driven Progress**: Due to the long-running nature of VS, all job states must be persistently tracked in SQLite, surviving server restarts.

---

## 2. Component Architecture

### A. Data Models (Persistence Layer)
We will extend `core/models.py` (or create a dedicated schema) with:
- **`ScreeningJob`**: Tracks the overall batch run.
  - Fields: `id`, `workspace_id`, `receptor_path`, `grid_config`, `total_ligands`, `completed_ligands`, `status` (Queued, Running, Completed, Failed).
- **`ScreeningHit`**: Tracks individual docking results within a job.
  - Fields: `id`, `screening_job_id`, `ligand_name`, `smiles`, `best_affinity`, `status`, `pose_data_path`.

### B. Service Layer (`services/screening_service.py`)
This service acts as the orchestrator.
- **Library Parsing**: Handles bulk uploads (multi-structure SDF or CSV of SMILES).
- **Task Queuing**: Converts each molecule into a discrete preparation and docking task.
- **Concurrency Management**: Uses Python's `asyncio.Semaphore` or a `ProcessPoolExecutor` (limited to `os.cpu_count() - 1`) to run Vina concurrently without locking the FastAPI event loop.

### C. Execution Integration (Avoiding Debt)
The `screening_service.py` will explicitly import and reuse:
- `api.routes.docking_workspace.generate_ligand_3d` for standardizing input ligands.
- `docking_workflow.run_docking.run_vina` for the actual docking step.
- `docking_workflow.interaction_analyzer` for post-processing the top hits.

---

## 3. Workflow Sequence

1. **Job Configuration (Frontend)**
   - User navigates to `/virtual-screening`.
   - User selects an existing prepared receptor from their `Workspace` history.
   - User uploads a ligand library file.
   - User clicks "Start Screening".

2. **Job Initialization (Backend)**
   - `ScreeningJob` row is created. Status = `Running`.
   - The file is parsed into N ligands. `total_ligands` is updated.

3. **Concurrent Execution (Background Task)**
   - A background worker pool begins processing ligands.
   - **Step 1**: Ligand 3D preparation (if SMILES provided) -> PDBQT.
   - **Step 2**: Vina execution against the cached Receptor PDBQT.
   - **Step 3**: Database `ScreeningHit` row updated with `best_affinity`.
   - **Step 4**: `completed_ligands` counter incremented.

4. **Hit Analysis (Post-Processing)**
   - Once all ligands are processed, the system identifies the Top N hits (e.g., Top 10%).
   - The `interaction_analyzer.py` automatically maps H-bonds, water bridges, and metal contacts for these top hits.
   - (Optional) `docking_expert.py` is invoked to write a quick batch summary.

---

## 4. Frontend Design (`templates/virtual_screening.html`)

The UI will follow the established application design language:
- **Header**: Status banner indicating active screening jobs.
- **Left Panel (Configuration)**:
  - Workspace Receptor Dropdown (fetching from `/api/workspace/recent`).
  - File Upload zone (SDF/CSV).
  - Advanced config (Exhaustiveness override).
- **Right Panel (Live Dashboard)**:
  - Progress bar powered by Alpine.js polling `/api/screening/{job_id}/progress`.
  - A live-updating data table (using HTMX or Alpine) showing the top hits sorted by affinity as they complete.
  - A "View in Pose Analysis" button next to completed hits, routing directly to the existing `pose_analysis.html` view (achieving 100% UI reuse for visualization).

## 5. Potential Bottlenecks & Mitigations
- **CPU Starvation**: Vina is highly multi-threaded. If we run 8 Vina instances with `exhaustiveness=8` on an 8-core machine, context switching will destroy performance.
  - *Mitigation*: The `screening_service.py` must intelligently calculate `concurrency = max(1, total_cores // vina_threads_per_job)`.
- **Database Locks**: Rapid updates to the SQLite database from multiple threads.
  - *Mitigation*: Batch database updates or use WAL mode in SQLite. 
