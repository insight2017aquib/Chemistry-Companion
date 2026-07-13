# Backend Structure

Chemistry Companion uses a robust, layered FastAPI backend designed for stability and scalability. The architecture enforces strict separation of concerns.

## 1. Routing Layer (`api/`)
This is the boundary between the HTTP world and the Python application.
- **Rules**: Routers MUST NOT contain raw scientific logic. They are responsible for:
  1. Receiving HTTP requests and validating payloads using Pydantic (`api/schemas/`).
  2. Passing validated data to the Service Layer.
  3. Formatting the output back into HTTP JSON responses or HTML templates.
- **Location**: `api/routes/`

## 2. Service Layer (`services/`)
This layer orchestrates complex operations. 
- **Rules**: Services encapsulate business logic. A single API request (like running docking) might require calling protein preparation, gridbox calculation, Vina execution, and database persistence. The Service Layer coordinates these calls so the Router remains clean.
- **Examples**: `docking_workspace_service.py`, `spectra_service.py`, `ai/recommendations.py`.

## 3. Domain Modules (`docking_workflow/`, `spectra/`, `core/`)
These are pure Python modules that know nothing about HTTP or FastAPI. They execute the actual scientific algorithms.
- **`docking_workflow/`**: Contains scripts that execute AutoDock Vina via `subprocess.run`, parse PDBQT files, and detect protein pockets. 
  - *Note*: Execution of Vina (`vina_runner.py`) uses temporary files to prevent cross-contamination and is subject to timeout limits to prevent server hanging.
- **`core/`**: Shared foundational tools, including `openbabel_utils.py` for molecular conversions.

## 4. Database Layer (`database/`)
- **Engine**: SQLite managed by SQLAlchemy.
- **Purpose**: Persists historical job runs, session metadata, and batch processing results. It allows the user to revisit previous docking jobs without re-running computations.

## Architectural Flow Example (Docking)
1. **API**: `POST /api/docking/run` receives JSON payload.
2. **Validation**: Pydantic validates grid dimensions are floats.
3. **Service**: `DockingWorkspaceService.run_docking()` is invoked.
4. **Domain**: `run_vina()` executes the docking binary.
5. **Persistence**: `DockingWorkspaceService` saves the result to the SQLite DB.
6. **API**: JSON response is returned to the HTMX/Alpine frontend.
