# Architecture Map

This document maps the primary directories and files within the Chemistry Companion repository.

## Root Level
- `chemistry_companion.py`: Legacy or secondary entry point.
- `run.py`: Primary application entry point to start the Uvicorn server.
- `requirements.txt`: Python package dependencies.

## `api/` (API Layer)
Contains the FastAPI application setup and HTTP route definitions.
- `app.py`: FastAPI application initialization and middleware configuration.
- `routes/`: Contains all route modules (`docking.py`, `spectra.py`, `analysis.py`, etc.).
- `schemas/`: Pydantic models defining the API request and response bodies.

## `services/` (Service Layer)
Orchestrates business logic, tying together the API layer and the core processing engines.
- `docking_workspace_service.py`: Orchestrates the docking workflow, protein preparation, and job tracking.
- `spectra_service.py`: Orchestrates NMR/IR predictions.
- `ai/`: Contains AI integration services like `provider_manager.py` and `recommendations.py`.

## `core/` (Core Utilities)
Shared utilities used across the entire application.
- `openbabel_utils.py`: Wrappers around OpenBabel for molecule format conversion.
- `llm_utils.py`: Legacy or core LLM abstractions.
- `molecule_utils.py`: Core molecule parsing and handling.

## `docking_workflow/` (Domain: Docking)
Specialized logic for the protein docking pipeline.
- `protein_analysis.py`: Extracts metrics, sequences, and structures from PDB.
- `protein_preparation.py`: Prepares proteins (charges, water removal).
- `vina_runner.py`: Subprocess wrapper for executing AutoDock Vina.
- `pocket_detection.py`: Identifies binding pockets.
- `water_analysis.py` / `protonation.py`: Advanced preparation algorithms.

## `spectra/` (Domain: Spectroscopy)
Specialized logic for predicting chemical spectra.
- `proton_nmr.py`: 1H-NMR prediction algorithms.
- `carbon_nmr.py`: 13C-NMR prediction algorithms.
- `ir_predictor.py`: Infrared spectra estimation.

## `database/` (Data Persistence)
- `models.py`: SQLAlchemy ORM definitions for Users, Sessions, DockingJobs, etc.

## `templates/` & `static/` (Frontend)
- `templates/`: Jinja2 HTML templates. Notable files include `dashboard.html` and `docking_workspace.html` (which contains complex Alpine.js states).
- `static/`: Static assets (CSS, JS, images).

## `docs/` (Documentation)
Contains the project memory, architecture decisions, and developer guides.
