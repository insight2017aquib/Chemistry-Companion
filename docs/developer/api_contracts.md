# API Contracts

This document outlines the high-level API design and primary routes for Chemistry Companion.

## RESTful Design
The application relies heavily on RESTful endpoints defined using FastAPI, located in the `api/routes/` directory.

### Docking API (`/api/docking/`)
Coordinates the entire protein preparation, gridbox generation, and AutoDock Vina execution.
- `POST /api/docking/protein_prepare`: Cleans a PDB file, removing water and adding charges to produce a PDBQT.
- `POST /api/docking/receptor/analyze`: Comprehensive protein analysis returning chains, missing residues, and quality metrics.
- `POST /api/docking/receptor/ligand_sites`: Detects potential binding pockets based on co-crystallized ligands.
- `POST /api/docking/gridbox`: Calculates the bounding box (`center_x`, `size_x`, etc.) from a PDBQT file.
- `POST /api/docking/run`: Triggers the AutoDock Vina execution asynchronously or synchronously, returning a Job ID and poses.

### Spectra API (`/api/spectra/`)
Provides prediction capabilities for chemical structures.
- `POST /api/spectra/predict/nmr`: Predicts 1H and 13C NMR spectra for a given SMILES string.
- `POST /api/spectra/predict/ir`: Estimates the Infrared (IR) spectrum and identifies functional groups.

### AI Expert API (`/api/docking/ai_expert/`)
Provides targeted scientific reasoning.
- `POST /api/docking/ai_chain_recommendation`: Analyzes protein chains and recommends the most viable chain for docking based on structural integrity and active sites.
- `POST /api/docking/ai_expert/waters`: Evaluates water molecules and determines which should be retained (active site/catalytic) versus stripped (bulk).

## Data Schemas
Pydantic is used exclusively for request and response validation. Schemas are defined in `api/schemas/`. They ensure that malformed inputs immediately return HTTP 422 Unprocessable Entity, protecting the `services/` layer from invalid data.
