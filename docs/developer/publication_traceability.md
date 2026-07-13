# Publication Traceability Architecture

## 1. Core Principle
The Chemistry Companion AI Writer is strictly constrained to prevent the hallucination of scientific data, conclusions, or methodology. It achieves this via the **Traceability & Evidence Linking Architecture**.

## 2. Evidence Linking Flow
1. **Data Aggregation**: When a user requests a draft (e.g., Results for Campaign X), the backend queries SQLite for the exact `SeriesCompound` entities, their `properties` (ADMET/MPO), and `normalized_value` (Potency).
2. **Payload Packaging**: This data is serialized into a strict JSON payload.
3. **AI Generation Rules**: The `WRITER_SYSTEM_PROMPT` enforces that every claim (e.g., "Compound X had a pIC50 of 7.2") must cite a valid Entity ID from the payload.
4. **Separation of Concerns**: The AI is forced to separate text into:
   - `[Observed Data]`: Purely reporting the payload.
   - `[Derived Analysis]`: Explaining SAR trends.
   - `[AI Interpretation]`: Explicitly labeled hypotheses (e.g., "The AI hypothesizes this is due to steric clash...").

## 3. UI Traceability Viewer
In the `publication_studio.html`, the manuscript editor acts in tandem with the **Results Traceability Viewer**.
- The backend maps text spans to their corresponding `Entity IDs` (e.g., `cmp_001`, `exp_vina_4`).
- When a user highlights or clicks a drafted sentence, the Traceability panel decodes the `evidence_links` JSON and displays the exact database record that supports the claim.

## 4. Reproducibility Logs
For the Methods section, the `ReproducibilityLog` database table stores immutable snapshots of the environment:
- `python` version.
- `rdkit` version.
- `vina` (or other binaries) version.
- The exact `parameters` JSON passed to the execution function.
The AI is instructed to translate this JSON into narrative methodology, but is strictly forbidden from inventing missing parameters (e.g., if grid box size is `null`, it must state "standard parameters were utilized").
