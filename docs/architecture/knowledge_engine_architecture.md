# Scientific Knowledge Engine Architecture (Phase 14)

## 1. Objective
Transform Chemistry Companion from a data tracking system into an active Organizational Memory platform. The Knowledge Engine observes data across *multiple* projects and campaigns to extract, codify, and surface reusable "Lessons Learned" and "Scientific Rules."

## 2. Core Concepts
- **Knowledge Rule / Lesson Learned**: A formalized piece of scientific insight (e.g., "Replacing phenyl with pyridine improves solubility in Series A"). Crucially, all extracted rules are treated as **observed patterns**, not universal scientific facts.
- **Negative Knowledge**: The engine actively stores and prioritizes failures, liabilities, and activity cliffs to prevent repeated mistakes.
- **Confidence Scoring**: Rules are scored (Low, Moderate, High) dynamically based on three vectors: Evidence Volume, Project Diversity, and Consistency.
- **Contradiction Detection**: If a new rule contradicts an existing one (e.g., "Scaffold X works" vs "Scaffold X fails"), the system flags a Contradiction for manual review.
- **Rule Review Workflow**: Rules are extracted as "Pending" and must be manually approved by a human scientist before becoming part of the active Organizational Memory.
- **Cross-Project Pattern Mining**: Algorithms that detect repeated successes or failures across disparate campaigns (User-triggered, not automatic).
- **Scientific Librarian**: An AI interface capable of answering queries. The librarian *must* return: Answer, Evidence, Confidence, and Referenced Projects.

## 3. Database Schema Extensions
In accordance with non-destructive evolution:
- **`KnowledgeRule`**: `id`, `description`, `category` (SAR, ADMET, Scaffold), `confidence` (Low/Mod/High), `status` (Pending/Approved/Rejected), `evidence_payload` (JSON mapping to project/campaign/compound IDs), `provenance` (metadata regarding extraction), `version`, `created_at`.
- **`RuleContradiction`**: Tracks conflicting rules.

## 4. Components

### A. Service Layer
- **`KnowledgeMiningService` (`services/knowledge_miner.py`)**: 
  - User-triggered extraction scanning `OptimizationDecision` and `NotebookEntry` logs.
  - `calculate_confidence()`: Evaluates volume, diversity, and consistency.
  - `detect_contradictions()`: Flags opposing rules.
- **`MemorySearchService` (`services/memory_search.py`)**: Local BM25/inverted-index search. No external vector databases are used to maintain the lightweight SQLite footprint.

### B. AI Scientific Librarian
- **`AiScientificLibrarian` (`services/ai/scientific_librarian.py`)**:
  - Interrogates the `MemorySearchService` to answer natural language queries based purely on stored data.
  - Generates Cross-Project Failure/Success Analysis.

### C. UI & Visualization
- **`templates/knowledge_engine.html`**:
  - **Knowledge Dashboard**: High-level view of organizational rules.
  - **Memory Search**: Global search bar to query past experiments.
  - **Pattern Explorer**: Visualizing recurring liabilities.
