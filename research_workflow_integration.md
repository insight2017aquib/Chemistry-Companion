# Research Workflow Integration — Completion Report

| | |
|---|---|
| **Phase** | Research Workflow Integration (Phases 0–5) |
| **Date** | 2026-07-10 |
| **Goal** | Make **Research Project** the root entity; every module becomes a view over the current project; no manual IDs. |
| **Result** | ✅ Complete — **21/21** canonical workflow, **12/12** legacy migration, **24/24** RC1 regression |

---

## 1. Canonical Domain Model (as implemented)

```
ResearchProject                        (ROOT — everything is scoped by this)
├── 1:N  Portfolio            Portfolio.project_id
│         └── 1:N  OptimizationCampaign        Campaign.portfolio_id
│                    └── M:N  ChemicalSeries   CampaignSeriesLink
│                                └── 1:N  SeriesCompound
│                    └── 1:N  OptimizationDecision
├── 1:N  LiteratureReference / NotebookEntry
└── 1:N  PublicationWorkspace
          ├── 1:N  PublicationDraft  (+ evidence_links → entity IDs)
          └── 1:N  TableAsset

KnowledgeRule                 cross-project by default (project_id NULL); opt-in scoping
ScreeningWorkspace → ScreeningHit      a SOURCE, not a child of Series
MedChem Workbench                      project-agnostic series LIBRARY
```

Three corrections were made to the originally proposed tree, grounded in the schema:

1. **ADMET and MPO are not entities** — they are computed into `SeriesCompound.properties` (JSON). Derived views, never owned children. No tables were created for them.
2. **Screening Hits are not children of Series** — they belong to a `ScreeningWorkspace`; a Series *references* a hit via `screening_hit_id`. The arrow points **into** the series.
3. **ChemicalSeries has no single owning project — by design.** Because Campaign↔Series is M:N, "this project's series" is the **reachable set** through `Portfolio → Campaign → CampaignSeriesLink`. This is what allows comparing two campaigns that worked the same series.

---

## 2. What Was Broken (the root cause)

`database/models.py` declares **zero `ForeignKey` and zero `relationship()`** — every join key is a bare `String(50)` marked `# Logical FK`. Ownership was a *convention*, not a constraint, and several edges were never written at all:

| Edge | Before | After |
|---|---|---|
| Project → Portfolio | `link_portfolio()` **defined, never called** | `Portfolio.project_id`, written + read |
| Project → PublicationWorkspace | `create_workspace()` **never called** | wired on every draft |
| Workspace → Draft (+evidence) | `save_draft()` **never called** — drafts discarded | persisted, versioned |
| KnowledgeRule → Project | *no column existed* | `project_id` (NULL = cross-project) |
| Decision → Compounds | `compound_ids` JSON (not joinable) | unchanged — deferred (see §7) |

Consequence: the knowledge graph always returned `"portfolios": []`, Publication drafts were generated and thrown away, and the Results section (keyed by campaign) had no relational path to the bibliography (keyed by project).

---

## 3. Phases Delivered

**Phase 0 — Project context.** `api/project_context.py` exposes `get_current_project(project_id)`, resolved from the URL. Scoped pages live at `/project/{id}/{module}`; legacy URLs 307 → `/projects`. Because a scoped route *must* declare the dependency, **a page cannot be rendered without its research context** — this structurally eliminated the "template rendered but was passed no data" bug class (previously seen on `/admet`, `/publication`, `/knowledge-engine`), rather than patching each route.

**Phase 1 — Schema, migration, missing links.** `Portfolio.project_id`, `KnowledgeRule.project_id`, indexes on every logical FK, unique index on `CampaignSeriesLink`. Service-layer invariants (parent-exists → 400; idempotent series linking). Reachable-set queries: `portfolios_for_project`, `campaigns_for_project`, `series_for_project`.

**Phase 2 — Publication persistence.** `get_or_create_workspace()`, `project_id_for_campaign()` (Campaign → Portfolio → Project), auto-versioned `save_draft()` with a real `evidence_links` map, `save_table_asset()`, `GET /project/{id}/drafts`.

**Phase 3 — No manual IDs.** New `GET /api/lead-opt/campaign/{id}/compounds`. Both free-text boxes (`placeholder="camp_..."`, `placeholder="cmp_..."`) replaced by scoped selectors. A repo-wide grep for raw-ID placeholders returns **no matches**.

**Phase 4 — Context propagation.** Knowledge Engine stays **cross-project by default** (that breadth is its purpose) with an explicit "This Project Only" opt-in; rules carry a Cross-project / Project badge.

---

## 4. Migration Strategy

No Alembic. It is not installed, and adding a migrations directory + build dependency to an app headed for a Windows installer is real cost. `database/migrations.py` performs an **idempotent, dependency-free reconcile** at startup (`PRAGMA table_info` + `ALTER TABLE ADD COLUMN` + `CREATE INDEX IF NOT EXISTS`), safe on every boot. Alembic remains the right tool for the staged follow-up that adds real `ForeignKey` constraints (which require SQLite table rebuilds).

**Adoption is trigger-correct.** The original design said "run when no projects exist." The live database disproved it: it already had two user projects *and* an orphan `rpa` portfolio owning two real campaigns. Under that rule adoption would have been skipped forever; a naive series-only rule would have synthesized **duplicate** campaigns. The trigger is *"are there portfolios/series unreachable from any project?"*, and orphan **portfolios are adopted first**, preserving real structure:

```
Imported Research Project
├── rpa (adopted, user's)
│     ├── rpa-screening → QUIN-AZE (13 compounds)
│     └── rpa-lead      → QUIN-AZE (13 compounds)
└── Default Portfolio
      └── ATR Campaign  → ATR (13 compounds)      ← only the truly-orphaned series
```

Campaigns went 2 → 3 (+1), not 2 → 4. User projects `atr` / `rpa-hit` untouched.

---

## 5. Bug Found and Fixed During Integration

**`AIProviderManager._extract_json()` silently failed on every structured LLM call.**

The model returns valid JSON, then appends commentary containing *a second JSON object*:

```
{"patterns":[...]}                                   ← the answer
However... A more conservative answer: {"patterns": []}
```

The parser used `find("{")` … `rfind("}")`, so the slice spanned **both** objects and never parsed. `mine()` then degraded gracefully to 0 patterns — masked by the very error handling that was supposed to make it safe. This affected **every** `query_structured()` caller.

Fixed with a balanced-brace scan (skips string literals and escapes; advances past malformed candidates). Unit-tested against: pure JSON, fenced JSON, trailing prose, **trailing second JSON**, brace inside a string, escaped quotes, malformed-then-valid, and no-JSON. Mining went from **0 → 4** patterns.

Two RC1 latent 500s were also fixed on paths being touched: bad campaign in table export (500 → 404) and DOCX without python-docx (500 → 400).

---

## 6. Validation

### A. Canonical workflow, **fresh empty database** — 21/21
Create Project → Crossref literature + Notebook → Timeline → Portfolio → Series + compounds → Campaign (+link series) → Decisions → MPO dashboard → AI prioritization → ADMET radar → Publication draft.

Key assertions:
- Draft **persisted** with evidence map (`draft_… v1`) referencing the real `campaign_id`, `series_ids`, and 3 `cmp_…` IDs.
- **References** come from the project's linked literature (Crossref-resolved); **tables** reference the correct compounds.
- **Graph traverses Project → Portfolio → Campaign → Series → Compounds** (1p/1c/1s, 3 compounds) with 3 decisions recorded.
- **No screen asks for a raw ID** (all 5 scoped pages clean).
- **Isolation:** a second project sees none of the first project's campaigns or series.

### B. **Migrated legacy database** — 12/12
Schema upgraded; `Imported Research Project` created; user projects preserved; **no orphan portfolios remain**; **no duplicate campaigns**; ATR and QUIN-AZE intact at 13 compounds each; both reachable from the imported project; graph traverses (2p/3c/3s); the original `rpa` portfolio preserved; **migration idempotent** on re-run.

### C. RC1 regression, 9 modules — 24/24
Dashboard/nav, Molecular Workspace (SMILES, 2D, 3D, export-formats fix), Virtual Screening, MedChem (SAR data, real MMP transformations), ADMET, Lead Optimization, Research OS, Publication (CSV/LaTeX, 404/400 fixes), Knowledge Engine.

---

## 7. Remaining Debt (deliberate, scheduled)

- **`OptimizationDecision.compound_ids` is a JSON array**, not a join table. It blocks a truly relational evidence map. Slated with the real-FK migration as `DecisionCompoundLink`.
- **No real `ForeignKey` constraints.** Enforced in the service layer + indexes for now ("Both, staged"). SQLite requires full table rebuilds; that lands with Alembic pre-GA.
- **`candidate_status`** is stored inside `SeriesCompound.properties` JSON. Works; left alone deliberately.
- Cosmetic: Tailwind CDN and Plotly v1.58.5 console warnings — pin production assets before GA.

---

## 8. Answer to the Original Question

> *Can a medicinal chemist start with a new research project and finish with a publication draft without manually copying data between modules?*

**Yes.** Verified end-to-end on an empty database: the project is known from the URL, its portfolios and campaigns from the project, its compounds from the campaign, its references from its literature — and the resulting manuscript draft is persisted with an evidence map pointing back at the exact compounds it cites. The chemist selects; they never transcribe.
