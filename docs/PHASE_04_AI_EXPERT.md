# PHASE_04_AI_EXPERT.md

OBJECTIVE

Turn Chemistry Companion into an intelligent docking assistant.

TASKS

## AI Protein Preparation Expert

Combine:

Rule Engine
+
Structural Analysis
+
LLM Reasoning

For recommendations.

---

## Chain Expert

Example output:

Recommended Chain:
A

Confidence:
94%

Reason:
Contains catalytic residues.
Contains crystal ligand.
Highest completeness score.

---

## Water Expert

Explain:

Why keep water?

Why remove water?

Scientific reasoning required.

---

## Cofactor Expert

Explain:

Why keep ATP?

Why remove sulfate?

---

## Metal Expert

Explain:

Why retain Zn²⁺?

Why retain Mg²⁺?

Display catalytic importance.

---

## Pocket Expert

Rank pockets.

Explain ranking.

Provide druggability interpretation.

---

## AI Assistant Panel

Add frontend panel:

Ask Protein Expert

Example questions:

Why is chain A recommended?

Why should Zn be retained?

Why is this pocket ranked first?

Why is quality score low?

---

## Consensus System

Use:

Groq
Gemini
OpenRouter

Optional voting.

Return:

consensus recommendation
confidence

---

DELIVERABLES

AI Expert System

AI Assistant Panel

Consensus Engine

Documentation

ADR entries

Tests
