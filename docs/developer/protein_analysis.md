# Protein Analysis Engine

## Overview
The Chemistry Companion features a dedicated scientific protein analysis layer designed to support intelligent receptor preparation and docking. It performs deep heuristic analysis on raw PDB inputs without relying on AI, generating structured metadata for the frontend and LLM pipelines.

## Capabilities

### 1. Chain Analysis
- Detects residue count per chain.
- Identifies missing residues (via REMARK 465).
- Detects bound ligands, cofactors, metals, and crystallographic waters per chain.
- Generates a "chain score" and recommends the most viable chain for docking.

### 2. Water Analysis
- Classifies crystallographic waters into:
  - **Active-site waters**: Waters within interaction distance of the bound ligand or predicted pocket.
  - **Conserved waters**: Highly coordinated waters critical for structural integrity.
  - **Bulk waters**: Surface solvent that should typically be stripped.

### 3. Cofactor Analysis
- Detects known cofactors (ATP, ADP, NAD, NADH, FAD, FMN, HEME, SAM, CoA).
- Classifies cofactors as `Required` (catalytic), `Optional`, or `Artifact`.

### 4. Metal Analysis
- Detects common transition metals (Zn, Mg, Fe, Mn, Cu, Ni, Co, Ca).
- Identifies coordinating residues in the protein.
- Assesses catalytic relevance.

### 5. Quality Assessment
- Generates a global structure score (0–100) based on crystallographic resolution, number of missing residues, active-site integrity, and chain completeness.

## API Endpoints
All endpoints are mounted under `/api/docking` and utilize the `ProteinAnalyzeRequest` schema:
- `POST /api/docking/protein/analyze`: Full rich receptor analysis.
- `POST /api/docking/protein/chains`: Detailed per-chain summaries.
- `POST /api/docking/protein/waters`: Water classification and recommendations.
- `POST /api/docking/protein/cofactors`: Cofactor detection and status.
- `POST /api/docking/protein/metals`: Metal detection and coordination logic.
- `POST /api/docking/protein/quality`: Resolution and structural integrity scoring.

## Code Structure
- **Core Logic**: `docking_workflow/protein_analysis.py`, `docking_workflow/water_analysis.py`
- **Routing**: `api/routes/docking_workspace.py`
- **Schemas**: `api/schemas/docking.py`
- **Tests**: `tests/test_api_docking_workspace_protein_endpoints.py`
