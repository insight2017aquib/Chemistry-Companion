# Autonomous Research Workflow Engine Architecture

## 1. Objective
Transform the disparate toolsets of Chemistry Companion into an integrated, orchestratable pipeline. The Workflow Engine enables users to stitch together steps (Docking -> ADMET -> Knowledge Mining -> Publication) into reusable templates, governed by specialized agents and strict human-in-the-loop approval gates.

## 2. Core Entities
- **Workflow Template**: A predefined graph of steps (e.g., "Hit Discovery Pipeline").
- **Workflow Step**: An individual action (e.g., "Run Vina Docking", "Generate SAR Table").
- **Workflow Run**: A specific execution instance of a Template, tracking inputs, outputs, runtime, and status.
- **Approval Gate**: A specialized `Workflow Step` that halts execution until a user manually clicks "Approve" or "Reject".
- **Specialized Agent**: Context-aware AI services that execute specific steps and recommend actions.

## 3. Specialized Agents Architecture
Instead of a single monolithic AI, we split responsibilities:
- `DockingAgent`: Analyzes poses and sets up grid boxes.
- `MedChemAgent`: Suggests SAR optimizations and scaffold hops.
- `ADMETAgent`: Flags liabilities (e.g., PAINS, high LogP).
- `KnowledgeAgent`: Mines historical failures from Phase 14.
- `PublicationAgent`: Drafts text from Phase 13.
All agents communicate via the central Workflow Engine, which acts as the orchestrator.

## 4. Database Schema
- **`WorkflowTemplate`**: `id`, `name`, `description`, `graph_payload` (JSON definition of steps and edges).
- **`WorkflowRun`**: `id`, `template_id`, `status` (Running, Waiting for Approval, Completed, Failed), `state_payload` (current inputs/outputs), `start_time`, `end_time`.
- **`WorkflowStepLog`**: `id`, `run_id`, `step_name`, `agent_name`, `status`, `log_output`.

## 5. Principle: Humans Decide
The system explicitly forbids autonomous execution of critical steps.
- **Allowed autonomously**: Filtering libraries, running Vina, calculating Lipinski.
- **Requires Approval Gate**: Promoting a hit to a lead, finalizing a publication draft, approving a Knowledge Rule.
