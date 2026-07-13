# Workflow Engine Developer Guide

## 1. How Workflows are Defined
Workflows are defined as Directed Acyclic Graphs (DAGs) stored in the `WorkflowTemplate.graph_payload` JSON.
Example Payload:
```json
{
  "nodes": [
    {"id": "step1", "type": "DockingAgent.run_virtual_screen", "config": {"threshold": -8.0}},
    {"id": "step2", "type": "ApprovalGate", "message": "Approve Top Hits?"},
    {"id": "step3", "type": "PublicationAgent.draft_results"}
  ],
  "edges": [
    {"from": "step1", "to": "step2"},
    {"from": "step2", "to": "step3"}
  ]
}
```

## 2. Execution Engine (`services/workflow_engine.py`)
The engine reads the DAG and executes nodes sequentially.
When it hits an `ApprovalGate`, it updates the `WorkflowRun` status to `Waiting for Approval` and suspends execution.
The UI polls or displays notifications. When the user approves, the API hits `/api/workflow/resume/{run_id}`, and the engine continues to the next node.

## 3. Extending Agents
To add a new capability to the workflow engine, create a method on a Specialized Agent (e.g., `MedChemAgent.run_mpo_scoring`). Register this method string in the UI's Workflow Builder palette so users can drag-and-drop it into their custom pipelines.

## 4. Notifications
A lightweight SSE (Server-Sent Events) or basic polling notification system must be implemented in the frontend to alert users when a workflow completes or requires human intervention.
