# First Run Experience — Validation Report

**Role:** Release QA Lead  
**Date:** 2026-07-13  
**Scope:** FRE integration validation only (no feature work, no package rebuild)  
**Method:** Isolated runtime (`CHEM_COMPANION_RUNTIME_DIR` under temp), FastAPI `TestClient`, automated scenario suite  
**Raw results:** `fre_validation_raw.json`  

---

## Final decision

# **READY TO REBUILD WINDOWS PACKAGE**

| Metric | Count |
|--------|------:|
| **PASS** | **79** |
| **FAIL** | **0** |
| **WARNING** | **0** (see notes below for untested live API keys) |

All automated scenario checks passed. No validation failure requires a code fix before rebuild.

---

## Executive summary

| Area | Result |
|------|--------|
| Fresh install → `/setup` redirect | **PASS** |
| Wizard UI loads | **PASS** |
| Skip → limited mode, no crash | **PASS** |
| OpenRouter / Groq / OpenAI configure + `.env` + no leaks | **PASS** |
| Ollama host/port + friendly failure | **PASS** |
| Scientific tool detection | **PASS** |
| Workspace dirs / writability | **PASS** |
| Settings → Setup Wizard | **PASS** |
| Post-setup: no auto-wizard | **PASS** |
| Regression (modules, export, analysis) | **PASS** |
| Security (keys not in API/UI/logs) | **PASS** |

**Note on AI “connection succeeds”:** QA used **synthetic invalid keys**. Providers correctly returned friendly rejection (`API key was rejected`). Live success with production keys was **not exercised** in this environment (no real secrets in CI). The test-connection pipeline, storage, and masking are validated; optional manual smoke with real keys is recommended once after rebuild.

---

## Scenario results

### Scenario 1 — Fresh installation

| Check | Status | Detail |
|-------|--------|--------|
| `needs_first_run` True | **PASS** | Isolated root, no `.env` / marker |
| Redirect `/` → `/setup` | **PASS** | HTTP **307**, `Location: /setup` |
| Wizard launches | **PASS** | `/setup` 200, Welcome / Begin Setup present (~29 KB) |
| API `needs_setup` true | **PASS** | `/api/setup/status` |

### Scenario 2 — Skip setup

| Check | Status | Detail |
|-------|--------|--------|
| Skip finish succeeds | **PASS** | `AI_PROVIDER=disabled`, setup complete |
| Marked complete | **PASS** | `needs_first_run` → false |
| Dashboard / VS / MedChem / Analysis | **PASS** | All HTTP 200, **no** re-redirect to setup |
| AI providers endpoint no crash | **PASS** | 200, 4 providers listed |

Limited functionality: app usable without AI; no stack traces.

### Scenario 3 — OpenRouter

| Check | Status | Detail |
|-------|--------|--------|
| Test Connection (invalid key) | **PASS** | Friendly: “API key was rejected…” |
| No key leak in test response | **PASS** | |
| Finish / `.env` updated | **PASS** | Key stored on disk only |
| Key stored in `.env` | **PASS** | |
| Status API no full key | **PASS** | Masked e.g. `sk-o••••••••••••_001` |
| Masked summary | **PASS** | |
| Live connection with **valid** key | *Not run* | Requires real `OPENROUTER_API_KEY` |

### Scenario 4 — Groq

| Check | Status | Detail |
|-------|--------|--------|
| Test Connection (invalid key) | **PASS** | Friendly rejection |
| No key leaks | **PASS** | test-ai, finish, status |
| `.env` updated + key stored | **PASS** | |
| Live connection with **valid** key | *Not run* | Requires real `GROQ_API_KEY` |

### Scenario 5 — OpenAI

| Check | Status | Detail |
|-------|--------|--------|
| Test Connection (invalid key) | **PASS** | Friendly rejection |
| No key leaks | **PASS** | |
| `.env` updated + key stored | **PASS** | |
| Live connection with **valid** key | *Not run* | Requires real `OPENAI_API_KEY` |

### Scenario 6 — Ollama

| Check | Status | Detail |
|-------|--------|--------|
| Connection test (service absent) | **PASS** | Friendly: cannot reach local service |
| Bad port failure handling | **PASS** | Port 1 → ok=false, no traceback |
| Host/port written to `.env` | **PASS** | `OLLAMA_HOST`, `OLLAMA_PORT` |

### Scenario 7 — Scientific tool detection

| Check | Status | Detail |
|-------|--------|--------|
| Returns tool list | **PASS** | 5 tools |
| RDKit | **PASS** | installed |
| Open Babel | **PASS** | installed |
| AutoDock Vina | **PASS** | installed |
| Java | **PASS** | installed |
| OPSIN | **PASS** | installed |
| Missing tools non-blocking | **PASS** | Status field only; wizard continues |

### Scenario 8 — Workspace

| Check | Status | Detail |
|-------|--------|--------|
| Output / log / workspace dirs created | **PASS** | Under isolated runtime |
| Database parent exists | **PASS** | |
| Paths writable | **PASS** | All four checks true |
| API `ensure-dirs` | **PASS** | “Directories are ready.” |

### Scenario 9 — Settings integration

| Check | Status | Detail |
|-------|--------|--------|
| Settings shows Setup Wizard | **PASS** | Link / card present |
| `/setup?force=1` opens wizard | **PASS** | 200 |
| Configuration reloads | **PASS** | Status returns provider + paths |
| Saving updates `.env` | **PASS** | e.g. `AI_PROVIDER=disabled` |
| Optional samples | **PASS** | 3 sample files copied |

### Scenario 10 — Application startup after setup

| Check | Status | Detail |
|-------|--------|--------|
| `needs_first_run` false | **PASS** | |
| Dashboard without setup redirect | **PASS** | `/` → 200 |
| After module reload still complete | **PASS** | Simulates process restart logic |

### Scenario 11 — Regression

| Check | Status | Detail |
|-------|--------|--------|
| Dashboard | **PASS** | |
| Virtual Screening | **PASS** | |
| MedChem | **PASS** | |
| Projects | **PASS** | |
| Analysis page | **PASS** | |
| Exports page | **PASS** | |
| Settings | **PASS** | |
| ADMET (project-scoped) | **PASS** | |
| Lead Optimization | **PASS** | |
| Research OS | **PASS** | |
| Publication | **PASS** | |
| Knowledge Engine | **PASS** | |
| Export formats + CSV | **PASS** | |
| Analysis pipeline (HTMX) | **PASS** | ethanol SMILES, ~10 KB HTML |
| AI providers endpoint | **PASS** | |
| Database | **PASS** | App lifespan DB init |

---

## Security

| Check | Status |
|-------|--------|
| No full secrets in `/api/setup/status` | **PASS** |
| No full secrets in `/api/setup/tools` | **PASS** |
| No full secrets in `/settings` HTML | **PASS** |
| No full secrets in `/setup` HTML | **PASS** |
| No full secrets in test-ai error body | **PASS** |
| Keys only in local `.env` file | **PASS** (verified on disk for S3–S5) |
| Masked display uses bullets | **PASS** |

No evidence of API keys in exceptions returned to the client. Stack traces were not returned for AI test failures.

**Screenshots:** Not captured in this automated run (headless API/UI response validation). Manual screenshot optional before public marketing; not required for rebuild gate.

---

## Known issues / residual notes

| ID | Severity | Note |
|----|----------|------|
| K1 | Low | Live **successful** connection with production OpenRouter/Groq/OpenAI keys not tested here (invalid keys only). |
| K2 | Low | Ollama success path not tested (no local Ollama service in QA environment); failure path validated. |
| K3 | Info | Browser **console** not instrumented (no Playwright run); keys are not rendered unmasked in server HTML/JSON checked. |
| K4 | Info | FRE is source-level; **Windows onedir/installer still need rebuild** to ship wizard to end users. |

None of these block the rebuild decision.

---

## Recommendations

1. **Proceed to rebuild** PyInstaller onedir + Inno Setup so FRE ships in `ChemistryCompanion-3.0.0-Setup.exe`.  
2. After rebuild, optional **manual 5-minute smoke**: fresh VM install → wizard → one real API key Test Connection → Finish → restart → confirm no wizard.  
3. Keep treating missing scientific tools as warnings only (already implemented).  
4. Do not document “edit `.env` by hand” for end users; Settings → Setup Wizard is the supported path.

---

## Conclusion

```text
READY TO REBUILD WINDOWS PACKAGE
```

FRE integrates correctly with Chemistry Companion: first-run redirect, skip/limited mode, multi-provider configuration, tool detection, workspace paths, settings re-entry, post-setup normal startup, regression modules, and security checks all passed automated validation with **zero FAILs**.
