# AI Docking Expert Architecture

## Overview
The AI Docking Expert (Phase 7) provides medicinal chemistry interpretations of docking outputs without overriding the deterministic physics engines (AutoDock Vina, RDKit, OpenBabel).

## Core Principle
**"AI explains. AI does not override docking results. Scientific calculations remain authoritative."**

The system enforces this principle via strict LLM system prompts (`EXPERT_SYSTEM_PROMPT` in `docking_expert.py`), ensuring the LLM:
1. Treats input interactions and binding affinities as absolute truth.
2. Does not invent non-covalent interactions.
3. Does not dispute rank order.

## Prompt Architecture

### 1. Pose Interpretation (`explain_pose`)
**Purpose**: Explain the energetic and geometric drivers of a single binding mode.
**Inputs**: Ligand SMILES, Pose Affinity, Array of detected interactions (H-bonds, Water Bridges, Metal Coordination).
**Output Strategy**: Group by interaction type; explain how each contributes to binding using medicinal chemistry principles.

### 2. Pose Comparison (`compare_poses`)
**Purpose**: Highlight structural and energetic differences between multiple binding modes.
**Inputs**: Ligand SMILES, Array of Pose data (Ranks, Affinities, Interactions).
**Output Strategy**: Analyze flipped/rotated relative orientations, explain affinity deltas based strictly on interaction differences, and identify conserved contacts.

### 3. Ligand Improvements (`suggest_improvements`)
**Purpose**: Suggest text-based SAR and hit-to-lead optimizations.
**Inputs**: Ligand SMILES, Best Pose Data, Best Pose Interactions.
**Output Strategy**: Suggest substituent modifications (e.g., adding halogens), bioisosteres, and optimization of current H-bonds. Explicitly forbidden from generating raw SMILES modifications (to avoid hallucinated structures).

### 4. Docking Report (`generate_report`)
**Purpose**: Synthesize a comprehensive Markdown Executive Summary.
**Inputs**: Job Metadata, Ranked Poses, Complete Interaction map.
**Output Strategy**: Produce a 4-section report (System Overview, Binding Energetics, Key Interactions, Optimization Outlook).

## Endpoint Integration
Endpoints are implemented in `api/routes/llm_explanation.py`:
- `POST /api/llm/expert/pose`
- `POST /api/llm/expert/compare`
- `POST /api/llm/expert/improve`
- `POST /api/llm/expert/report`

These endpoints return HTML fragments designed to be seamlessly hot-swapped into the `pose_analysis.html` frontend via HTMX.
