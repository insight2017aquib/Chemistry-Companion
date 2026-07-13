# Deep Engineering Audit: Research Tools Subsystem

This document serves as the exhaustive, implementation-grade technical specification of the Chemistry Companion Research Tools subsystem. **No code modifications were made during this audit.**

---

## SECTION 1: END-TO-END EXECUTION TRACE

### 1. Virtual Screening
**Flow:** Sidebar Menu → `virtual_screening.html` → JS Event (Submit Form) → `fetch('/start')` → `api/routes/virtual_screening.py (start_screening)` → `Depends(get_db)` → `ScreeningService.create_job` → `Database (ScreeningWorkspace insert)` → `BackgroundTasks (run_screening_job)` → Returns JSON `{"job_id": "...", "status": "queued"}` → DOM Update (Alpine state sets active job, starts polling).
**Files involved:** `templates/virtual_screening.html`, `api/routes/virtual_screening.py`, `services/screening_service.py`, `database/models.py`.

### 2. MedChem Workbench
**Flow (Analyze SAR):** Sidebar Menu → `medchem_workbench.html` → JS `runAiSar()` → `fetch('/api/medchem/series/{id}/ai-sar', POST)` → `api/routes/medchem.py (ai_sar_analysis)` → `Depends(get_db)` → `MedchemService.get_compounds` → `MedChemExpertService.analyze_sar_trends` → `AIProviderManager.query` → Returns HTML fragment → DOM Update (`document.getElementById('ai-sar-content').innerHTML = HTML`).
**Files involved:** `templates/medchem_workbench.html`, `api/routes/medchem.py`, `services/medchem_service.py`, `services/ai/medchem_expert.py`, `services/ai/provider_manager.py`.

### 3. ADMET & Developability
**Flow (Dashboard Load):** Sidebar Menu → `admet_workbench.html` → JS `loadSeries(id)` → `fetch('/api/admet/series/{id}/dashboard')` → `api/routes/admet.py (get_admet_dashboard)` → `Depends(get_db)` → DB Query `SeriesCompound` → Returns HTMX string with `data-stats` JSON payload → DOM Update (`innerHTML = HTML`) → `initRadarCharts()` parses JSON and builds Chart.js.
**Files involved:** `templates/admet_workbench.html`, `api/routes/admet.py`, `database/models.py`.

### 4. Lead Optimization
**Flow (Log Decision):** Sidebar Menu → `lead_opt_studio.html` → JS `submitDecision()` → `fetch('/api/lead-opt/campaign/{id}/decision', POST)` → `api/routes/lead_opt.py (log_decision)` → `CampaignService.record_decision` → DB Query (Snapshots `SeriesCompound` properties) → DB Insert (`OptimizationDecision`) → Returns JSON `{"status": "success"}` → DOM Update (`loadCampaign()` re-fetches dashboard).
**Files involved:** `templates/lead_opt_studio.html`, `api/routes/lead_opt.py`, `services/campaign_service.py`.

### 5. Research OS
**Flow (Add Notebook):** Sidebar Menu → `research_os.html` → JS `submit()` or HTMX trigger → `POST /api/research-os/project/{id}/notebook` → `api/routes/research_os.py (add_notebook_entry)` → `ProjectService.add_notebook_entry` → DB Insert (`NotebookEntry`) → Returns HTML `<script>htmx.trigger('body', 'refreshTimeline');</script>` → DOM Update (Timeline refreshes).
**Files involved:** `templates/research_os.html`, `api/routes/research_os.py`, `services/project_service.py`.

### 6. Publication Assistant
**Flow (Draft Results):** Sidebar Menu → `publication_studio.html` → JS `draftResults()` → `fetch('/api/publication/ai/draft-results', POST)` → `api/routes/publication.py (draft_results)` → DB Query (`OptimizationCampaign`, `SeriesCompound`) → `ScientificWriterService.draft_results_section` → `AIProviderManager.query` → Returns HTML string → DOM Update (injects text into textarea, injects **Mock HTML** into traceability viewer).
**Files involved:** `templates/publication_studio.html`, `api/routes/publication.py`, `services/ai/scientific_writer.py`.

### 7. Knowledge Engine
**Flow (Mine Patterns):** Sidebar Menu → `knowledge_engine.html` → HTMX `hx-post="/api/knowledge-engine/mine"` → `api/routes/knowledge_engine.py (trigger_mining)` → `KnowledgeMinerService.mine_cross_project_patterns` → DB Query (Finds "solubility" in Discarded Decisions) → DB Insert (`KnowledgeRule`) → Returns HTML block → DOM Update (Re-renders page fragment).
**Files involved:** `templates/knowledge_engine.html`, `api/routes/knowledge_engine.py`, `services/knowledge_miner.py`.

---

## SECTION 2: FRONTEND AUDIT

### `virtual_screening.html`
- **Controls:** Form (Grid params, Library file upload, Exhaustiveness dropdown). Table (Polling results). Buttons (Start Screening, Promote Hit, Triage).
- **Target API:** `/api/virtual-screening/*`
- **Status:** **Working**. All fetch/HTMX calls map to valid endpoints.

### `medchem_workbench.html`
- **Controls:** New Series Form, Add Compound Form, Import Form, SAR Tabs.
- **Charts:** Chart.js bubble plot (`id="sarChart"`).
- **Status:** **Partial / Mocked**. `initPlot()` hardcodes an array `[{x: 2.5, y: 7.2, r: 10}, ...]`. It completely ignores backend data.

### `admet_workbench.html`
- **Controls:** Series selection sidebar, Run AI button.
- **Charts:** Chart.js radar charts dynamically created from `data-stats` attribute.
- **Status:** **Working Frontend / Weak Backend**. The frontend maps data correctly, but the data is based on weak backend heuristics.

### `lead_opt_studio.html`
- **Controls:** Campaign list, What-If Form, Log Decision modal.
- **Charts:** Chart.js bubble plot (`id="mpo-scatter-chart"`).
- **Status:** **Working Frontend**. The scatter plot correctly parses JSON injected by the backend in the `data-points` attribute.

### `research_os.html`
- **Controls:** Project tabs, Notebook input, Timeline view, Graph view.
- **Status:** **Working**.

### `publication_studio.html`
- **Controls:** Campaign select, Format select, Draft button, Caption Generator, Table download links.
- **Status:** **Partial / Mocked**. The `draftResults()` javascript function explicitly contains dummy HTML for the traceability panel: `<strong>Entity:</strong> cmp_001_hit...`.

### `knowledge_engine.html`
- **Controls:** Mine Button, Ask Librarian form, Approve/Reject buttons.
- **Status:** **Working Frontend / Broken Backend**. Frontend calls endpoints successfully, but the backend uses rudimentary strings.

---

## SECTION 3: BACKEND AUDIT (FastAPI Routes)

| Route File | Endpoint | Method | Params | Service Called | Status / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `medchem.py` | `/series/{id}/compounds` (GET) | GET | `series_id` | `MedchemService` | Returns HTML table of compounds. Used by HTMX. |
| `medchem.py` | `/series/{id}/import` | POST | `file`, `column_map` | `ImportService` | Works. Relies on JSON mapping. |
| `admet.py` | `/series/{id}/dashboard` | GET | `series_id` | DB Queries | Returns HTMX with radar data JSON. Traffic light logic baked into router. |
| `lead_opt.py`| `/campaign/{id}/dashboard` | GET | `campaign_id` | `CampaignService.calculate_compound_mpo` | Generates JSON for scatter plot in route and renders HTML. |
| `publication.py`| `/table/campaign/{id}` | GET | `campaign_id`, `format` | `PublicationService.generate_compound_table` | Returns raw CSV, LaTeX, or DOCX response. Working. |
| `knowledge_engine.py`| `/mine` | POST | None | `KnowledgeMinerService.mine_cross_project_patterns` | Triggered by HTMX. Returns concatenated success message and re-rendered template. |

---

## SECTION 4: SERVICE AUDIT

| Service | Responsibilities | AI / RDKit / External | Placeholder / Missing |
| :--- | :--- | :--- | :--- |
| `MedchemService` | Compound creation, properties. | RDKit `Descriptors`, `Lipinski`, `sascorer`. | `detect_mmp()` uses a >75% common substructure heuristic instead of true matched pair clipping. |
| `CampaignService` | MPO calculations, decision ledger. | None. | `generic_mpo` uses hardcoded weights if none provided. Assumes missing parameters like pKa. |
| `ProjectService` | Notebooks, Literature, DOIs. | `requests` (Crossref API). | `DOI_CACHE` is a simple memory dict. Will clear on server restart. |
| `KnowledgeMinerService` | Rule extraction, contradiction finding. | BM25 custom class. | **Highly stubbed.** Only triggers if the word "solubility" exists in exactly 3+ failed decisions. |
| `PublicationService` | Table formatting, Citations. | `csv`, `openpyxl`, `docx`. | Fully functional, but citation formats are hardcoded string interpolations. |

---

## SECTION 5: DATA FLOW

**Workflow: AI Triage (Virtual Screening)**
`[Input: job_id]` → Validation (Check DB for job) → Transformation (Query top 10 hits, cluster by Murcko scaffold) → Business Logic (`DockingExpertService.ai.query(prompt)`) → Transformation (`_sanitize_report_html` regex cleaner) → `[Output: Clean HTML Fragment]`

**Workflow: MPO Calculation (Lead Opt)**
`[Input: Compound Properties]` → Validation (Check if values exist) → Business Logic (`MpoEngine.pfizer_cns_mpo` / `generic_mpo`) → Transformation (Normalize to 10-pt scale) → `[Output: Float score]`

---

## SECTION 6: MOCK DETECTOR

1. **`templates/medchem_workbench.html` (Lines 376-407):**
   - **Where:** `initPlot()` javascript function.
   - **What:** `data: [{x: 2.5, y: 7.2, r: 10}, {x: 3.1, y: 8.1, r: 12}... ]`
   - **Replacement:** The endpoint `/api/medchem/series/{id}/compounds` should return JSON alongside the HTML, and Alpine.js should consume that JSON.

2. **`templates/publication_studio.html` (Lines 227-235):**
   - **Where:** `draftResults()` javascript function.
   - **What:** `document.getElementById('traceability-panel').innerHTML = '<div class="bg-emerald-50..."><strong>Entity:</strong> cmp_001_hit...</div>';`
   - **Replacement:** The AI `draft_results` endpoint needs to generate structured JSON containing `{"html": "...", "citations": [...]}`.

3. **`services/knowledge_miner.py` (Line 63):**
   - **Where:** `mine_cross_project_patterns()`
   - **What:** `sol_failures = [d for d in failed_decisions if "solubility" in (d.rationale or "").lower()]`
   - **Replacement:** Replace hardcoded string check with a clustering algorithm (e.g., HDBSCAN on embeddings) or an LLM call to extract recurring failure modes.

4. **`services/medchem_service.py` (Line 126):**
   - **Where:** `detect_mmp()`
   - **What:** `ratio1 >= 0.75 and ratio2 >= 0.75`
   - **Replacement:** Implement standard Hussain-Rea fragmentation using RDKit's `FragmentOnBonds`.

---

## SECTION 7: AI AUDIT

All AI expert services (`medchem_expert.py`, `developability_expert.py`, `lead_opt_expert.py`, `research_assistant.py`, `scientific_writer.py`, `scientific_librarian.py`, `docking_expert.py`) instantiate `AIProviderManager()` from `services/ai/provider_manager.py`.

- **Connectivity:** They are **ACTUALLY CONNECTED** to LLMs. They form a prompt string, prepend a SYSTEM PROMPT, and call `self.ai.query()`.
- **ProviderManager:** Handles fallback chains (e.g., Groq → DeepSeek → OpenRouter → Gemini). It parses responses.
- **Mocking:** None of the Python AI services return mock strings. The *appearance* of mocking is entirely due to frontend shortcuts (e.g. Publication Traceability Viewer).

---

## SECTION 8: DATABASE AUDIT

**Core Models Used by Research Tools:**
- `ChemicalSeries`, `SeriesCompound`: MedChem, ADMET.
- `OptimizationCampaign`, `Portfolio`, `CampaignSeriesLink`, `OptimizationDecision`: Lead Optimization.
- `ResearchProject`, `NotebookEntry`, `LiteratureReference`, `ProjectPortfolioLink`: Research OS.
- `KnowledgeRule`, `RuleContradiction`: Knowledge Engine.
- `PublicationWorkspace`, `PublicationDraft`: Publication Assistant.

**Observations:**
- Relationships are cleanly defined.
- `candidate_status` is stored loosely inside the JSON `properties` column of `SeriesCompound` by the `CampaignService` to respect DB evolution constraints.

---

## SECTION 9: VISUALIZATION AUDIT

- **Virtual Screening Progress:** Real data. HTMX polling.
- **MedChem SAR Chart (Chart.js):** **MOCKED.** Hardcoded in JS.
- **ADMET Radar (Chart.js):** Real data. Backend computes it, pushes via `data-stats` attribute into the DOM, JS renders it.
- **Lead Opt MPO Scatter (Chart.js):** Real data. Backend computes it, pushes via `data-points` attribute into the DOM, JS renders it.
- **Research OS Knowledge Graph (Vis.js):** Real data. Fetches `/api/research-os/project/{id}/graph`.

---

## SECTION 10: BROKEN CONNECTIONS

| Frontend Control | JS Function | API | Backend | Status |
| :--- | :--- | :--- | :--- | :--- |
| MedChem SAR Tab | `initPlot()` | None | None | **MOCK** (Hardcoded JS) |
| Publication Traceability | `draftResults()` | `/api/publication/ai/draft-results` | `ScientificWriterService` | **BROKEN/MOCK** (API returns HTML, JS forces mock trace string) |
| Knowledge Engine Mine | N/A (HTMX) | `/api/knowledge-engine/mine` | `KnowledgeMinerService` | **PARTIAL** (Works, but logic is hardcoded) |

---

## SECTION 11: FILE HEALTH

| File | Purpose | Size | Status / Action Needed |
| :--- | :--- | :--- | :--- |
| `templates/medchem_workbench.html` | UI | 22KB | Needs Refactor: Remove Chart.js dummy data. |
| `templates/publication_studio.html` | UI | 16KB | Needs Refactor: Handle JSON from AI rather than raw HTML. |
| `services/knowledge_miner.py` | Logic | 4KB | Needs Refactor: Implement real NLP/LLM pattern extraction. |
| `services/ai/provider_manager.py` | Infrastructure | 20KB | Healthy. Excellent provider failover logic. |

---

## SECTION 12: IMPLEMENTATION READINESS

| Module | Backend % | Frontend % | Integration % | Est. Work |
| :--- | :--- | :--- | :--- | :--- |
| Virtual Screening | 100% | 100% | 100% | Complete |
| MedChem Workbench | 85% | 80% | 80% | Medium |
| ADMET & Developability | 70% | 90% | 90% | Hard (Better Heuristics) |
| Lead Optimization | 90% | 100% | 100% | Easy |
| Research OS | 100% | 100% | 100% | Complete |
| Publication Assistant | 95% | 75% | 75% | Medium |
| Knowledge Engine | 20% | 90% | 20% | Hard |

---

## SECTION 13: PATCH PLAN

**Patch 1: MedChem SAR Plot Integration**
- **Files Affected:** `api/routes/medchem.py`, `templates/medchem_workbench.html`
- **Action:** Alter `/series/{id}/compounds` GET endpoint to return `{ "html": "...", "plot_data": [...] }`. Update `fetchCompounds()` to inject HTML and call `initPlot(data.plot_data)`.
- **Risk:** Low.

**Patch 2: Publication Traceability JSON Enveloping**
- **Files Affected:** `services/ai/scientific_writer.py`, `api/routes/publication.py`, `templates/publication_studio.html`
- **Action:** Modify the AI prompt to enforce structured JSON output: `{"draft_html": "...", "citations": [{"id": "cmp_001", "claim": "..."}]}`. Update `/ai/draft-results` to parse this and return JSON. Update frontend `draftResults()` to render the citations dynamically in the Traceability Viewer.
- **Risk:** Medium (Prompt engineering required).

**Patch 3: Refactor Knowledge Miner**
- **Files Affected:** `services/knowledge_miner.py`
- **Action:** Replace the hardcoded `if "solubility" in...` block. Collect all rejected decisions in the DB, group by campaign, and feed them to `AIProviderManager.query_structured()` asking the LLM to identify recurring thematic failure modes. Use the LLM output to populate `KnowledgeRule`.
- **Risk:** Medium.

**Patch 4: Enhance MMP Detection Algorithm**
- **Files Affected:** `services/medchem_service.py`
- **Action:** Import RDKit `FragmentOnBonds`. Write a loop that cleaves acyclic single bonds between heavy atoms for two molecules, groups fragments by core/R-group, and flags true matched pairs where cores match and R-groups differ.
- **Risk:** Hard (Cheminformatics logic).

---
*Audit Complete. System requires strategic un-mocking and heuristic replacement to achieve production readiness.*
