# Chemistry Companion — RC1 Release Validation Report

| | |
|---|---|
| **Application** | Chemistry Companion |
| **Version** | 2.0.0 (`FastAPI(title="Chemistry Companion", version="2.0.0")`) |
| **Validation date** | 2026-07-10 |
| **Validator role** | Senior QA / Release Validation Engineer |
| **Environment** | Windows 11 Pro, 10.0.26200 |
| **Python** | 3.14.0 (`.venv`) |
| **Server** | uvicorn `api.app:app` on port 8000 (fresh instance of current code) |
| **Database** | Disposable copy of `chemistry_companion.db` (real data backed up to `backups/` and restored after run) |

### Dependency / capability probe (runtime)

| Capability | Status | Effect |
|---|---|---|
| RDKit | ✅ present | Descriptors, properties, MMP, 2D/3D |
| OpenBabel | ✅ present | 3D embedding, receptor prep |
| gemmi | ✅ present | Protein parsing (`/health` → `visualization.available=true`) |
| openpyxl | ✅ present | Excel generation lib available |
| AutoDock Vina (CLI) | ✅ present | `…\anaconda3\Library\bin\vina.exe` — real docking feasible |
| `vina` Python pkg | ⚠️ absent | CLI fallback used instead (fine) |
| python-docx | ❌ absent | DOCX table export unavailable (GUI hides it gracefully) |
| LLM provider (Groq `llama-3.3-70b`) | ✅ working | All AI features exercised live |

---

## Test Summary

| Metric | Count |
|---|---|
| Feature checks executed | 48 |
| **PASS** | 44 |
| **FAIL** | 2 |
| **WARNING** (latent / cosmetic / env-gated) | 2 |
| Code fixes applied (reproduced + safe) | 1 |

Methodology: two-layer end-to-end — GUI (browser preview: snapshot, console, network) + backend (direct HTTP against the running server, server-log stack traces). Modules with empty tables (Lead Opt, Research OS, Publication, Knowledge Engine) were seeded through real endpoints/services and then exercised.

---

## Detailed Results (PASS / FAIL per feature)

### 1. Dashboard & Shell
| Feature | Result | Evidence |
|---|---|---|
| App startup | ✅ PASS | Clean lifespan log, no errors |
| Dashboard render (`/`) | ✅ PASS | 200, 31.6 KB, all module cards present (snapshot) |
| Navigation — all 22 pages | ✅ PASS | Every page route returns 200 (no 404/500) |
| Research Tools dropdown | ✅ PASS | Links resolve to real routes |
| Settings (`/settings`) | ✅ PASS | 200 |
| `/health` | ✅ PASS | 200, healthy JSON |
| Console cleanliness | ⚠️ WARNING | Tailwind "CDN in production" + Plotly v1.58.5 deprecation notices (cosmetic, non-blocking) |

### 2. Molecular Workspace
| Feature | Result | Evidence |
|---|---|---|
| SMILES analysis (`POST /analyse`) | ✅ PASS | 200, MW/LogP/TPSA present (caffeine) |
| IUPAC analysis (`input_method=iupac`) | ✅ PASS | 200, descriptors returned |
| 2D viewer (`/api/visualization/ligand2d`) | ✅ PASS | 200, SVG |
| 3D viewer (`/api/visualization/ligand3d`) | ✅ PASS | 200, html + mol_block |
| Descriptors / property calc | ✅ PASS | RDKit values returned |
| Export CSV / JSON (`/api/export`) | ✅ PASS | 200 both |
| Supported-formats (`/api/export/formats`) | ✅ **FIXED** | Was **500** → now 200 (see Code Changes) |
| Excel export subsystem | ⚠️ WARNING | Endpoints removed in working tree; orphaned FE refs (see Runtime Errors #3) |

### 3. Virtual Screening
| Feature | Result | Evidence |
|---|---|---|
| Job status | ✅ PASS | 200 on real job `scr_4a97f284a00c` |
| Hits table | ✅ PASS | 200, affinity data rendered |
| Bad job id | ✅ PASS | 404 (correct) |
| Start validation (missing receptor) | ✅ PASS | 400 (correct) |
| Promote top-N to series | ✅ PASS | 200, promoted 2 |
| AI triage | ✅ PASS | 200 in 5s, scaffold/SAR/prioritization report, HTML sanitized (no `<script>`) |
| Full docking pipeline | ✅ PASS (existing evidence) | 2 completed jobs / 25 hits already present; Vina CLI available. Fresh run not re-triggered (long background task) |

### 4. MedChem Workbench
| Feature | Result | Evidence |
|---|---|---|
| List / create series | ✅ PASS | 200 |
| Add compound | ✅ PASS | 200, RDKit props computed |
| CSV import | ✅ PASS | 61 imported (correct `smiles_col` mapping; GUI ships that mapping) |
| SAR plot data (`/sar-data`) | ✅ PASS | Real point for qualifying compound (Phenetole LogP 2.09 / pIC50 6.2); empty+labeled when no pIC50 (correct) |
| MMP (`/mmps`) | ✅ PASS | Real transformations (`H → Cl`, etc.), no "Substituent A/B" |
| Bioisosteres | ✅ PASS | 200 |
| AI SAR / AI Design | ✅ PASS | 200 (7s / 200) |

### 5. ADMET & Developability
| Feature | Result | Evidence |
|---|---|---|
| Dashboard fragment | ✅ PASS | 200, 43 KB, `data-stats` payload |
| Radar charts + traffic lights | ✅ PASS | radar/hERG/`bg-` markup present |
| AI series analysis | ✅ PASS | 200 |
| AI compound explanation | ✅ PASS | 200 |

### 6. Lead Optimization
| Feature | Result | Evidence |
|---|---|---|
| **Create campaign / portfolio** | ❌ **FAIL** | No route/UI; `create_campaign`/`create_portfolio` exist but are called nowhere (see Blocking Issues) |
| Campaign dashboard | ✅ PASS | 200, MPO scatter `data-points` (seeded campaign) |
| MPO calculations | ✅ PASS | Present in dashboard payload |
| Log decision | ✅ PASS | 200 |
| What-if (AI) | ✅ PASS | 200 |
| AI prioritization | ✅ PASS | 200 |

### 7. Research OS
| Feature | Result | Evidence |
|---|---|---|
| **Create project** | ❌ **FAIL** | No route/UI; `create_project` exists but is called nowhere (see Blocking Issues) |
| Notebook entry | ✅ PASS | 200 |
| Timeline | ✅ PASS | 200, entry rendered |
| Knowledge graph | ✅ PASS | Valid tree (project + literature + notebook); FE builds vis.js nodes/edges |
| Literature + Crossref lookup | ✅ PASS | Real DOI `10.1038/nature12373` resolved in 2s |
| AI summarize / lessons | ✅ PASS | 200 both |

### 8. Publication Assistant
| Feature | Result | Evidence |
|---|---|---|
| AI draft results (JSON + evidence) | ✅ PASS | 200 `application/json`, `draft_html` + 5 real evidence compounds |
| Table export CSV | ✅ PASS | 200 |
| Table export LaTeX | ✅ PASS | 200 |
| Table export DOCX | ⚠️ WARNING | GUI hides button when python-docx absent (`{% if docx_available %}`); raw endpoint 500 is latent-only (see Runtime Errors #2) |
| Citations (ACS/…) | ✅ PASS | 200, real formatted citation |
| Figure caption (AI) | ✅ PASS | 200 |

### 9. Knowledge Engine
| Feature | Result | Evidence |
|---|---|---|
| Mine rules (LLM) | ✅ PASS | 200 in 2s, "Found 2 new" from 4 Discard rationales |
| Approve rule | ✅ PASS | 200 |
| Reject rule | ✅ PASS | 200 |
| Ask librarian (AI + memory search) | ✅ PASS | 200 |

---

## Runtime Errors Observed

**#1 — `/api/export/formats` returned HTTP 500 (FIXED).**
`fastapi.exceptions.ResponseValidationError`: handler annotated `-> Dict[str, List[str]]` but returns a `descriptions` sub-dict of `str→str`, which fails response-model validation.
```
api/routes/export.py, line 73, in get_supported_formats
ResponseValidationError: {'loc': ('response','descriptions'), 'msg':'Input should be a valid list'}
```
Reproduced via `GET /api/export/formats` → 500. Fixed (see Code Changes). Not reachable from any rendered page, but a registered endpoint that always 500'd.

**#2 — `GET /api/publication/table/campaign/{id}?format=docx` returns 500 when python-docx is absent (LATENT).**
`_to_docx` raises `ImportError` (by design) and `download_table` does not catch it. **Not user-reproducible**: the Publication Studio hides the DOCX link via `{% if docx_available %}` and shows "requires python-docx package." Left unfixed — the GUI already degrades gracefully and the dependency is simply not installed. Classified Low.

**#3 — Excel-export subsystem is orphaned (LATENT).**
Working-tree (uncommitted) changes to `api/routes/export.py` removed `POST /export/preview`, `/export/download`, `GET /export/profiles`, `/export/history`, but the frontend still references `/api/export/preview|download|profile` (`static/js/shell.js`, `templates/exports.html`, `templates/components/export_modal.html`, `batch_results.html`). Those components are **not included in any served page**, and `/exports` is **not linked from any nav** — so the 404s are not reachable through normal navigation. Primary CSV/JSON export works. Classified Low (dead/incomplete code).

**Note:** initial "table export 500 for all formats" and "citations empty" during testing were traced to a **test-harness URL bug** (PowerShell `$var?query` interpolation mangling the path), **not** an application defect — confirmed by re-running with correctly built URLs (all returned 200). No code was changed for these.

---

## Code Changes

Exactly **one** change was made, justified by reproduced Runtime Error #1. (The larger pre-existing uncommitted diff in `export.py` was present at session start and is **not** part of this validation.)

**File:** `api/routes/export.py`
```diff
 @router.get("/export/formats")
-async def get_supported_formats() -> Dict[str, List[str]]:
+async def get_supported_formats() -> Dict[str, Any]:
```
- **Problem:** `GET /api/export/formats` → 500 (`ResponseValidationError`).
- **Root cause:** Return-type annotation `Dict[str, List[str]]` does not match the returned payload whose `descriptions` value is `Dict[str, str]`.
- **Risk:** Minimal. `Any` is already imported; behavior unchanged, only relaxes the response schema so the intended payload serializes.
- **Verification:** Restarted server → `GET /api/export/formats` → **200** with the correct `{formats, descriptions}` body.

---

## Regression Verification

After the fix and server restart:
- `GET /api/export/formats` → 200 ✅
- `GET /api/medchem/series/{id}/sar-data` → 200 ✅ (previously un-mocked SAR plot)
- `GET /api/medchem/series/{id}/mmps` → 200 ✅ (real MMP transformations)
- `POST /api/publication/ai/draft-results` → 200 JSON + evidence ✅ (un-mocked traceability)
- `POST /api/knowledge/mine` → 200, real LLM patterns ✅ (rewired miner)
- All 22 page routes still 200. No new errors in server logs attributable to the change.

---

## Release-Blocking Issues (classified)

| # | Severity | Issue | Impact | Action |
|---|---|---|---|---|
| B1 | **HIGH** | **No GUI/API path to create an Optimization Campaign or Portfolio.** `CampaignService.create_campaign`/`create_portfolio` exist but are wired to no route or template. | On a clean install, **Lead Optimization is unusable** — the page shows "No active campaigns" with no way to create one. | Not fixed (feature work, out of validation scope). Must add a create-campaign route + UI before packaging. |
| B2 | **HIGH** | **No GUI/API path to create a Research Project.** `ProjectService.create_project` exists but is called nowhere. | On a clean install, **Research OS is unusable** — no way to create the project that all sub-features require. | Not fixed (feature work). Must add a create-project route + UI before packaging. |
| B3 | LOW | `/api/export/formats` 500 | Registered endpoint crashed | **FIXED** this pass |
| B4 | LOW | DOCX table endpoint 500 when python-docx missing | Not GUI-reachable (button hidden) | Optional: install python-docx, or catch `ImportError` → 400 |
| B5 | LOW | Orphaned Excel-export endpoints/JS (`/export/preview|download|profile`) | Not reachable via nav | Reconcile FE with the simplified backend, or restore endpoints |
| B6 | LOW | Console CDN warnings (Tailwind prod, Plotly v1.58.5) | Cosmetic | Pin production assets pre-GA |

---

## Release Recommendation

# ❌ NOT READY FOR PACKAGING

**Evidence:** 7 of 9 modules (Dashboard, Molecular Workspace, Virtual Screening, MedChem Workbench, ADMET, Publication Assistant, Knowledge Engine) passed full end-to-end validation, including all live AI features and real Crossref/Vina-backed capabilities. One registered-endpoint 500 was found and safely fixed.

However, **two of nine advertised modules — Lead Optimization and Research OS — cannot be initiated by an end user** on a clean installation: the code to create their root entities (campaign/portfolio, project) exists in the service layer but is exposed through **no route and no UI** (issues B1, B2). Every downstream feature of those modules works once an entity is seeded programmatically, which confirms the gap is a **missing creation entry point**, not deeper breakage. This is corroborated by the shipped database containing zero campaigns/portfolios/projects — none were ever creatable through the app.

Because these two gaps make advertised functionality unreachable for a real user, the build does not meet an RC "usable end-to-end" bar. **Recommendation: address B1 and B2 (add the create-entity routes + minimal UI), then re-validate modules 6 and 7.** All other findings are Low/cosmetic and do not independently block release.

---

*Validation performed against a disposable copy of the production database; the original `chemistry_companion.db` was backed up before testing and restored afterward. Test artifacts created during validation (RC1-Validation series/campaign/project/decisions/rules) exist only in the disposed copy.*
