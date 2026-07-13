# Release Blocker Resolution — Chemistry Companion

| | |
|---|---|
| **Phase** | Release Blocker Resolution (post RC1 validation) |
| **Date** | 2026-07-10 |
| **Scope** | Resolve ONLY the two HIGH blockers from `release_validation.md` (B1, B2). No new science, no redesign. |
| **Environment** | Windows 11 (26200), Python 3.14.0, uvicorn `api.app:app` :8000, disposable DB |
| **Result** | ✅ Both blockers resolved and validated end-to-end from an empty database |

---

## 1. Files Modified

| File | State | Change |
|---|---|---|
| `api/routes/lead_opt.py` | new (untracked) | Added `GET /portfolios`, `POST /portfolio`, `POST /campaign` — thin routes over `CampaignService` |
| `api/routes/research_os.py` | new (untracked) | Added `POST /project` — thin route over `ProjectService.create_project` |
| `templates/lead_opt_studio.html` | new (untracked) | Added "New Campaign" sidebar card + Alpine state/methods (`createPortfolio`, `createCampaign`); dynamic `newCampaigns` list |
| `templates/research_os.html` | new (untracked) | Added "New Project" sidebar card + Alpine `createProject`; dynamic `newProjects` list |
| `api/app.py` | modified | Fixed the served `/lead-opt` and `/research-os` page routes to query and pass `campaigns` / `projects` (secondary root cause — see §2) |

No other modules were touched. All changes reuse existing services, templates, and dashboards.

---

## 2. Root Cause

**B1 / B2 (primary):** The creation logic already existed —
`CampaignService.create_portfolio()`, `CampaignService.create_campaign()`, `CampaignService.link_series_to_campaign()`, and `ProjectService.create_project()` — but **was exposed through no API route and no UI**. On a fresh install the Lead Optimization and Research OS pages showed "No active campaigns/projects" with no way to create the root entity, making both modules unusable.

**Secondary cause (discovered during validation):** The **served** page routes `@app.get("/lead-opt")` and `@app.get("/research-os")` in `api/app.py` rendered their templates with `_page_ctx(request)` only — they never queried `OptimizationCampaign` / `ResearchProject`. (The data-passing handlers existed, but only at the unused router paths `/api/lead-opt/` and `/api/research-os/`.) So even after creation, the sidebar list stayed empty on page load. This was verified precisely: the DB and the JSON API endpoints saw the created rows, while the rendered page consistently did not.

---

## 3. Solution

**API (wired to existing services, no business logic added):**
- `POST /api/lead-opt/portfolio` → `CampaignService.create_portfolio(name, description)`
- `GET  /api/lead-opt/portfolios` → list for the create-campaign dropdown
- `POST /api/lead-opt/campaign` → `create_campaign(portfolio_id, name, goal_type, {})`, then `link_series_to_campaign()` if a series is chosen (validates the portfolio exists → 400 otherwise)
- `POST /api/research-os/project` → `ProjectService.create_project(name, target, objectives)`

**GUI (minimal, reuses existing dashboards):**
- Lead Opt: a "New Campaign" sidebar card — pick/create a Portfolio, name the Campaign, choose goal, optionally link an existing MedChem series. On submit it opens the **existing** campaign dashboard via the existing `loadCampaign()` and shows the new campaign in the list (Alpine `newCampaigns`).
- Research OS: a "New Project" sidebar card — on submit it opens the project via the existing `loadProject()` (timeline, graph, notebook, literature all unchanged) and shows it in the list (Alpine `newProjects`).

**Page-load correctness:** `api/app.py` `/lead-opt` and `/research-os` now query and pass `campaigns` / `projects`, so persisted entities appear in the sidebar after any reload.

Workflows delivered exactly as specified:
`Create Portfolio → Create Campaign → Open Campaign Dashboard` and `Create Project → Open Project → Notebook → Timeline → Knowledge Graph`.

---

## 4. Runtime Validation

Performed against a **freshly created empty database** (real DB stashed; app created a fresh schema on startup; restored afterward).

### Lead Optimization — full workflow (HTTP, empty DB)
```
confirm empty:  portfolios [] , series []
seed via app:   series ser_b9b3dc706e32 , compound cmp_a19e930c7c74 (Phenetole pIC50 6.4)
create portfolio  -> 200  port_8d220da181
create campaign   -> 200  camp_3fa6b39ccb  (linked to series)
open dashboard    -> 200  (MPO scatter present)
log decision      -> 200  {"status":"success"}
AI prioritization -> 200  (real LLM report)
```

### Research OS — full workflow (HTTP, empty DB)
```
create project    -> 200  proj_55551340e4
notebook entry    -> 200
timeline          -> 200  (entry rendered)
knowledge graph   -> 200  (project node + notebook present)
Crossref import   -> 200  DOI 10.1038/nature12373 resolved (~2s)
AI assistant      -> 200  (executive summary)
```

### Page-load list fix (after `api/app.py` change, server restarted)
```
GET /lead-opt     -> lists "Empty-DB Campaign"  : True
GET /research-os  -> lists "Empty-DB Project"    : True
```

### Regression
- `py_compile` clean on `api/app.py`, `api/routes/lead_opt.py`, `api/routes/research_os.py`.
- Existing endpoints unaffected: campaign dashboard, decision, what-if, ai-prioritize, notebook, timeline, graph, literature, AI all still 200.

---

## 5. Evidence (Browser GUI, driven through the live UI)

The create flows were exercised through the **actual Alpine components in the browser** (not just HTTP). Note: the harness screenshot renderer timed out on these pages, so evidence is DOM/state assertions captured live via the page context.

**Lead Optimization** (`/lead-opt`, driven via the component's own `createPortfolio()` / `createCampaign()`):
```json
{
  "before": { "portfolios": 2, "series": 1 },   // init() auto-loaded lists
  "afterPortfolios": 3,                          // createPortfolio worked
  "portfolioAutoSelected": true,
  "newCampaigns": ["GUI-Campaign"],              // appears in sidebar list
  "activeCampaignId": "camp_f6abc5c5a3",         // dashboard opened
  "dashboardScatterRendered": true               // MPO scatter canvas present
}
```

**Research OS** (`/research-os`, driven via `createProject()`):
```json
{
  "newProjects": ["GUI-Project"],
  "activeProjectId": "proj_6231674230",          // project opened
  "graphNetworkExists": true,                     // knowledge graph container rendered
  "timelineLoaded": true
}
```
Console showed no JavaScript errors (only the pre-existing cosmetic Plotly v1.58.5 / Tailwind-CDN deprecation notices, unrelated to this change).

---

## 6. Remaining Blockers

**None for the two targeted workflows.** Lead Optimization and Research OS are now fully usable from a clean install: create → open → operate.

Out-of-scope items already documented in `release_validation.md` and intentionally **not** changed here (all Low severity, none blocking):
- DOCX table-export endpoint returns 500 when `python-docx` is absent — but the GUI already hides the button (`{% if docx_available %}`), so it is not user-reachable.
- Orphaned Excel-export references (`/api/export/preview|download|profile`) from an earlier uncommitted backend simplification — not reachable through navigation.
- Cosmetic console warnings (Tailwind CDN in production, Plotly v1.58.5) — pin production assets pre-GA.

---

## Revised Recommendation

The two HIGH blockers that drove the **NOT READY** verdict in `release_validation.md` are resolved and validated end-to-end from an empty database, at both the API and GUI layers. With B1 and B2 cleared and no new blockers introduced, **Lead Optimization and Research OS now meet the "usable end-to-end" bar.** Subject to a final full-suite regression pass, the build is ready to advance toward packaging.
