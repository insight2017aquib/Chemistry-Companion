# Virtual Screening Architecture

## Overview
Phase 8 transforms the single-ligand docking workspace into a scalable Virtual Screening platform.
It relies heavily on reusability, executing the identical ligand preparation and Vina docking subroutines used in Phase 6, but orchestrated via `asyncio.Semaphore` pools.

## Data Models
We use SQLite via SQLAlchemy, defined in `database/models.py`.
- **ScreeningWorkspace**: Represents a single batch run. It holds a foreign key to the `Workspace` (the prepared receptor and grid).
- **ScreeningHit**: Represents a single processed ligand. Linked to `ScreeningWorkspace`.

## Concurrency Model
Rather than requiring Celery or Redis, which complicates the deployment of this desktop-oriented app, we use `asyncio` inside the FastAPI `BackgroundTasks`.

The worker limits parallel Vina threads based on `multiprocessing.cpu_count() // 2` to avoid system starvation.

## Clustering
When the batch completes, we use RDKit's `MurckoScaffold` module (in `services/clustering_service.py`) to group hits by their core scaffold. This significantly reduces redundancy when presenting top hits to the AI for triage.

## API Flow
1. **POST `/api/screening/start`**: Creates the models and launches the background task.
2. **GET `/api/screening/{job_id}/status`**: Returns JSON with progress metrics.
3. **GET `/api/screening/{job_id}/hits`**: Returns raw HTMX table rows for the dashboard.
4. **POST `/api/screening/{job_id}/triage`**: Calls the DockingExpertService to evaluate the clustered top hits.

## User Interface
The UI (`templates/virtual_screening.html`) uses Alpine.js to poll for status updates and reload the hits table dynamically without page refreshes.

Clicking "Review Pose" on a hit seamlessly redirects the user into the Phase 6 `pose_analysis.html` view by providing `job_id` and `hit_id` query params.
