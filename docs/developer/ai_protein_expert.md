# AI Protein Expert (Phase 5)

## Overview
The AI Protein Expert is an intelligent reasoning layer built on top of the AI Provider Architecture (Phase 2) and the Protein Analysis Engine (Phase 3). It utilizes Large Language Models (LLMs) to synthesize complex crystallographic metadata and provide actionable, domain-specific recommendations for receptor preparation.

## Core Recommendation Interfaces

The `services/ai/recommendations.py` module exposes five core functions that wrap the `AIProviderManager`:

1. **`recommend_chain()`**: Evaluates multi-chain PDBs. Reasons over missing residues, ligand proximity, and sequence length to suggest the single most biologically relevant chain for docking.
2. **`recommend_pocket()`**: Ingests fpocket/fob predicted binding sites alongside known crystallographic ligand sites to recommend the most druggable pocket based on volume, enclosure, and hydrophobicity.
3. **`recommend_waters()`**: Cross-references water interaction networks to advise which structural waters should be retained to mediate ligand binding versus bulk waters that should be stripped.
4. **`recommend_metals()`**: Differentiates catalytically essential transition metals from crystallization buffer artifacts.
5. **`recommend_cofactors()`**: Identifies vital coenzymes (e.g., FAD, NAD+) necessary for receptor integrity.

## AI Assistant Panel
The frontend `docking_workspace.html` integrates a reactive AI Assistant Panel (managed by Alpine variables like `assistantQuestion`, `assistantResponse`, `assistantDomain`). 
- Users can dynamically interrogate the AI about their specific protein.
- The backend `/api/docking/ai_expert/chain` (and similar domain routes) injects the full `ProteinAnalysis` JSON payload directly into the LLM prompt context automatically.
- This allows the AI to provide grounded, evidence-based answers without the user needing to copy-paste PDB sequences.

## Graceful Degradation
If no API keys (Groq, Gemini, DeepSeek, OpenRouter) are configured, or if the user is completely offline, the system degrades safely. The recommendation endpoints will intercept the failure and return heuristically determined suggestions (e.g., "Retain waters within 3Å of the ligand") alongside a `confidence: "low"` flag, ensuring the docking workflow is never blocked.
