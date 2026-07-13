# Installer Acceptance Validation — Chemistry Companion v3.0.0

| Field | Value |
|-------|-------|
| **Role** | Release QA Lead |
| **Artifact** | `dist/installer/ChemistryCompanion-3.0.0-Setup.exe` (~132 MB / 138,005,950 bytes) |
| **Date** | 2026-07-13 |
| **Platform** | Windows (per-user install, `%LOCALAPPDATA%\Programs\…`) |
| **Test install dir** | `%LOCALAPPDATA%\Programs\ChemistryCompanion-Acceptance` |
| **Mode** | Silent CURRENTUSER (`/VERYSILENT /CURRENTUSER`) as automated first-time user |
| **Raw evidence** | `installer_validation_raw.json`, `installer_validation_raw.csv`, `dist/installer/acceptance_logs/` |

---

## Release decision

# READY

The Windows installer meets first-time-user acceptance for install, First Run Experience (FRE), skip-AI path, OpenRouter configuration storage, research entity creation, module entry points, restart behaviour, upgrade data preservation, and uninstall policy.

---

## Executive summary

| Metric | Count |
|--------|------:|
| Checks executed (primary run) | 52 |
| **PASS** (primary + corrected S5/S6) | **52 effective** |
| **FAIL** (product defects) | **0** |
| **WARNING** | 2 (documented; none blocking) |

Five Scenario 6 page checks initially reported **FAIL (404)** in the automated harness. Root cause was a **QA script bug**: PowerShell automatic variable `$pid` (process ID) overwrote the research project id, so URLs hit `/project/3012/...` instead of `/project/proj_…/…`. A corrective revalidation with the correct project id (`proj_84717551f2`) returned **HTTP 200** for all project-scoped modules and successfully created Portfolio + Campaign. Those are not product defects.

Live OpenRouter success with a **real production API key** was not exercised in this run (synthetic key only). Invalid-key rejection, `.env` write, and key masking all passed.

---

## Scenario results

### Scenario 1 — Fresh Windows installation

**Expected:** Installation succeeds. No prior Chemistry Companion.

| Check | Status | Detail |
|-------|--------|--------|
| Installation succeeds | **PASS** | Exit code 0 |
| EXE present | **PASS** | `ChemistryCompanion.exe` |
| `_internal` present | **PASS** | Bundled runtime |
| FRE wizard template | **PASS** | `_internal\templates\setup_wizard.html` |
| No tests dir | **PASS** | Dev tests not shipped |
| Fresh no `.env` | **PASS** | Clean first-run state |
| Desktop shortcut | **PASS** | `Chemistry Companion.lnk` |
| Start Menu shortcut | **PASS** | Start Menu folder + shortcut |

**Verdict: PASS**

---

### Scenario 2 — Launch application / First Run Experience

**Expected:** FRE appears.

| Check | Status | Detail |
|-------|--------|--------|
| Process starts | **PASS** | Server process launches |
| Server ready | **PASS** | Listens on configured port |
| Redirect to setup | **PASS** | `GET /` → **307** → `/setup` |
| FRE wizard UI | **PASS** | Page contains “Begin Setup” (~30 KB HTML) |

Log evidence: install root and package root separated correctly; templates/static present; DB under install root.

**Verdict: PASS**

---

### Scenario 3 — Skip AI setup

**Expected:** Application works; friendly AI messages; no crashes.

| Check | Status | Detail |
|-------|--------|--------|
| Skip setup succeeds | **PASS** | `POST /api/setup/finish` → `ok=true`, “Configuration saved.” |
| App works after skip | **PASS** | `GET /` → 200, Dashboard content |
| Non-AI analysis works | **PASS** | `POST /api/analyse` SMILES `CCO` → 200, ~10 KB |
| AI endpoint no crash | **PASS** | `GET /api/llm/providers` → 200 |
| Friendly AI messaging | **PASS** | Settings shows configure / not-configured messaging |

**Verdict: PASS**

---

### Scenario 4 — Configure OpenRouter

**Expected:** API key path, connection test, `.env` persistence.

| Check | Status | Detail |
|-------|--------|--------|
| Test Connection responds | **PASS** | Endpoint returns structured message |
| Friendly reject invalid key | **PASS** | `ok=false`, “API key was rejected. Check the key and try again.” (no traceback) |
| OpenRouter `.env` updated | **PASS** | Finish with `provider=openrouter` succeeds |
| API key stored in `.env` | **PASS** | Key written under install root |
| No key leak in status API | **PASS** | Full key absent from status JSON |
| Key masked in status | **PASS** | Masked form shown (e.g. prefix + suffix) |

**Note:** Live successful OpenRouter chat with a real key was **not** part of this acceptance run. Storage, masking, and friendly failure path are validated.

**Verdict: PASS** (configuration path); live-key success deferred to optional smoke with secrets.

---

### Scenario 5 — Create Project / Portfolio / Campaign / Series / Compound

| Check | Status | Detail |
|-------|--------|--------|
| Create Project | **PASS** | e.g. `proj_8b06ab9a31` / revalidation `proj_84717551f2` |
| Create Portfolio | **PASS*** | Revalidation: `POST …/project/{id}/portfolio` → `port_a75698881c` |
| Create Campaign | **PASS*** | Revalidation: `POST /api/lead-opt/campaign` with `portfolio_id` → `camp_36ac56745f` |
| Create Series | **PASS** | e.g. `ser_2cb1f36ad95d` |
| Create Compound | **PASS** | Series compound create → 200 |

\* Primary automated run logged **WARNING** for Portfolio/Campaign because the harness used reserved `$pid` and wrong project path (`…/project/3012/portfolio` → 404). Correct IDs succeed.

**Verdict: PASS**

---

### Scenario 6 — Run modules (page load / API registration)

| Module | Status | Detail |
|--------|--------|--------|
| Virtual Screening | **PASS** | `GET /virtual-screening` → 200 |
| MedChem | **PASS** | `GET /medchem` → 200 |
| ADMET | **PASS*** | `GET /project/{projectId}/admet` → 200 (~17 KB) |
| Lead Optimization | **PASS*** | `GET /project/{projectId}/lead-opt` → 200 (~28 KB) |
| Research OS | **PASS*** | `GET /project/{projectId}/research-os` → 200 (~30 KB) |
| Publication | **PASS*** | `GET /project/{projectId}/publication` → 200 (~25 KB) |
| Knowledge Engine | **PASS*** | `GET /project/{projectId}/knowledge-engine` → 200 (~14 KB) |
| Screening API registered | **PASS** | OpenAPI paths contain screening |
| MedChem API registered | **PASS** | OpenAPI paths contain medchem |

\* Corrected after harness fix. Legacy unscoped `/admet`, `/lead-opt` correctly **307** → project picker (`/projects`).

**Scope note:** Acceptance verified module **entry pages load** and APIs are registered. Full end-to-end docking runs / long ADMET jobs were not part of this installer suite (covered by portable / science smoke elsewhere).

**Verdict: PASS**

---

### Scenario 7 — Restart (wizard no longer appears)

| Check | Status | Detail |
|-------|--------|--------|
| No wizard after restart | **PASS** | `GET /` → **200** Dashboard (no 307 to setup) |
| `.env` still present | **PASS** | Config survives process restart |

**Verdict: PASS**

---

### Scenario 8 — Upgrade (preserve user data)

**Method:** Re-run same Setup.exe against existing install dir (same AppId; simulates in-place upgrade of program files).

| Check | Status | Detail |
|-------|--------|--------|
| Upgrade install completes | **PASS** | Exit 0 (exit 5 also accepted if app-close warning) |
| Database preserved | **PASS** | `chemistry_companion.db` retained |
| Workspace preserved | **PASS** | Marker file + outputs path retained |
| Configuration preserved | **PASS** | `.env` retains setup/AI markers |
| EXE still present after upgrade | **PASS** | Application binary present |

**Verdict: PASS**

---

### Scenario 9 — Uninstall

| Check | Status | Detail |
|-------|--------|--------|
| Uninstaller present | **PASS** | ARP → `unins000.exe` |
| Uninstall exits | **PASS** | Exit 0 |
| Program EXE removed | **PASS** | `ChemistryCompanion.exe` gone |
| Desktop shortcut removed | **PASS** | |
| Start Menu shortcut removed | **PASS** | |
| App registry removed | **PASS** | App publisher key removed |
| User data preserved on uninstall | **PASS** | Policy: leave `.env`, DB, `logs`, `outputs` |
| `_internal` removed | **PASS** | Program payload removed |

Matches installer design: **program files uninstalled; user research data kept** under the former install directory unless the user deletes it manually.

**Verdict: PASS**

---

## PASS / FAIL / Warnings summary

### PASS (all scenarios)

- Fresh install, shortcuts, payload layout  
- FRE redirect + wizard UI  
- Skip AI → Dashboard + non-AI chemistry analysis  
- Friendly AI messaging; no crash on LLM endpoints  
- OpenRouter configure path: test connection, `.env` write, mask/no-leak  
- Project, portfolio, campaign, series, compound creation  
- All seven module surfaces load (VS, MedChem, ADMET, Lead Opt, Research OS, Publication, Knowledge Engine)  
- Restart skips wizard  
- Upgrade preserves DB / workspace / config  
- Uninstall removes program + shortcuts; keeps user data per policy  

### FAIL

**None (product).**

Initial automated FAILs on Scenario 6 were **false negatives** from the QA harness (`$pid` collision). Corrected revalidation: all **PASS**.

### Warnings

| ID | Item | Severity | Notes |
|----|------|----------|-------|
| W1 | Live OpenRouter with real API key | Low | Invalid-key path and `.env` storage verified; optional pre-release smoke with a real key recommended for marketing demos |
| W2 | Upgrade test used same Setup version | Low | Same AppId / same bits reinstall still validates data-preservation; a true N→N+1 binary upgrade should be re-checked when 3.0.1 ships |

---

## Recommendations

1. **Ship** `ChemistryCompanion-3.0.0-Setup.exe` for public Windows release.  
2. **Optional:** One manual or CI smoke with a real OpenRouter key (Test Connection + one AI feature).  
3. **Optional:** On next version, run silent upgrade **3.0.0 → 3.0.x** and re-assert DB / `.env` / outputs.  
4. **Docs:** State clearly that uninstall **preserves** research data (`.env`, database, logs, outputs) so users are not surprised.  
5. **QA harness:** Never assign to PowerShell `$pid`; use `$projectId` (or similar) for research project identifiers.

---

## Environment notes (end-user simulation)

- Install mode: **Current user** (no admin elevation required for default path under LocalAppData).  
- Runtime overrides used for automation only: `CHEM_COMPANION_OPEN_BROWSER=0`, host/port, `CHEM_COMPANION_RUNTIME_DIR` = install dir.  
- First-run markers: `.env` + setup-complete marker; middleware forces `/setup` until finish/skip.  
- After finish/skip: dashboard is default; wizard reachable from Settings when re-run intentionally.

---

## Decision matrix

| Gate | Result |
|------|--------|
| Installer installs cleanly | Yes |
| FRE works first launch | Yes |
| Usable without AI | Yes |
| AI config write path works | Yes |
| Core research objects creatable | Yes |
| Major module pages load | Yes |
| No wizard on restart | Yes |
| Upgrade preserves user data | Yes |
| Uninstall policy correct | Yes |
| Blocking product defects | **None** |

# READY

*Signed off as Release QA Lead — installer acceptance for Chemistry Companion 3.0.0 Windows Setup.*
