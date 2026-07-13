# Lead Optimization Studio Architecture (Phase 11)

## 1. Objective
Transform scattered Medicinal Chemistry workflows into structured, trackable Optimization Campaigns. This module acts as the "Command Center" for deciding which compounds to synthesize or advance next, driven by Multi-Parameter Optimization (MPO) and AI decision support.

## 2. Core Concepts
- **Portfolio**: The highest level of organization. A portfolio contains multiple Optimization Campaigns across different targets.
- **Optimization Campaign**: A parent entity that groups multiple Chemical Series under a unified goal type (e.g., "CNS Penetrant", "Peripheral Restrictive"). The goal type influences default MPO weights.
- **Decision Tracking**: A ledger of why specific compounds were promoted or discarded. Captures evidence, compounds involved, and AI rationale snapshots.
- **Multi-Parameter Optimization (MPO)**: Uses desirability functions (e.g. Pfizer MPO standard for CNS vs Non-CNS) to score compounds.
- **Candidate Status**: Tracking the lifecycle state: *Hit, Lead, Backup Lead, Needs Synthesis, Discarded*.

## 3. Database Schema Extensions
- **`Portfolio`**: `id`, `name`, `description`, `created_at`.
- **`OptimizationCampaign`**: `id`, `portfolio_id`, `name`, `target_profile`, `goal_type`, `mpo_weights` (JSON), `created_at`.
- **`CampaignSeriesLink`**: Association table linking `ChemicalSeries` to `OptimizationCampaign`.
- **`OptimizationDecision`**: `id`, `campaign_id`, `compound_ids` (JSON list), `decision_type`, `rationale`, `evidence_data` (JSON), `date`.

## 4. Components

### A. Service Layer
- **`CampaignService` (`services/campaign_service.py`)**: Manages CRUD for Portfolios, Campaigns, and Decisions. 
- **`MpoEngine`**: Within `CampaignService`. Implements Pfizer MPO desirability curves (LogP, MW, TPSA, HBD, pKa, basic pKa) alongside customizable Generic MPO scores.
- **`DesignSpaceService`**: Calculates PCA coordinates or basic property mapping for 2D visual tradeoff matrices.

### B. AI Lead Optimization Expert
- **`AiLeadOptExpert` (`services/ai/lead_opt_expert.py`)**: 
  - `prioritize_leads()`: Explains tradeoffs between candidates.
  - `what_if_analysis(compound, modification)`: Evaluates hypothetical structural changes against campaign MPO goals.
  - System prompt rigorously prevents speculative certainty.

### C. UI & Visualization
- **`templates/lead_opt_studio.html`**:
  - **Campaign Dashboard**: High-level view of all active series.
  - **Design Space Explorer**: Chart.js scatter plots visualizing Activity vs. Property space.
  - **Decision Ledger**: Timeline view of all historical decisions.
