# Portable Release Validation — Chemistry Companion 3.0 (with FRE)

**Date:** 2026-07-13  
**Scope:** PyInstaller **onedir** rebuild including validated First Run Experience; full smoke test of the packaged EXE  
**Installer:** **Not built** in this phase (portable must pass first)  
**Artifact:** `dist/ChemistryCompanion/ChemistryCompanion.exe`  

---

## Decision

# **PORTABLE BUILD PASSED**

Proceed to Windows installer rebuild when ready.

| Area | Result |
|------|--------|
| PyInstaller rebuild | **PASS** (exit 0) |
| FRE bundled (`setup_wizard.html`) | **PASS** |
| Cold start (frozen) | **PASS** (~10–12 s) |
| FRE redirect + wizard | **PASS** |
| Skip setup → `.env` | **PASS** |
| Core modules / analysis / export | **PASS** |
| Post-setup restart (no re-wizard) | **PASS** |
| Clean shutdown | **PASS** |

---

## Build

| Item | Detail |
|------|--------|
| Command | `python -m PyInstaller --noconfirm --clean chemistry_companion.spec` |
| Spec | `chemistry_companion.spec` |
| Entry | `portable_entry.py` |
| Exit code | **0** |
| EXE size | ~47.5 MB |
| Onedir size | ~395 MB (typical) |
| Log | `dist/portable_rebuild.log` |
| FRE template | `_internal/templates/setup_wizard.html` **present** |
| FRE Python modules | Included in PYZ/COLLECT (imported via `api.routes.first_run`, `services.first_run_service`) |

---

## Smoke test method

1. Run rebuilt `dist/ChemistryCompanion/ChemistryCompanion.exe` from its install directory.  
2. Clear portable first-run state: remove `{onedir}/.env` and `{onedir}/.cc_setup_complete`.  
3. Env: `CHEM_COMPANION_OPEN_BROWSER=0`, `HOST=127.0.0.1`, `PORT=8788`, `CHEM_COMPANION_RUNTIME_DIR` = onedir path.  
4. HTTP smoke against live frozen process (not TestClient / not system Python app).  

Evidence from process log and HTTP access log (uvicorn):

```text
Frozen=True
Package root = ...\dist\ChemistryCompanion\_internal
Install root = ...\dist\ChemistryCompanion
Templates=...\templates exists=True
VINA_BINARY=...\_internal\vina.exe
OBABEL_BINARY=...\_internal\obabel.exe
Starting ... http://127.0.0.1:8788
GET /setup 200
GET / 307 Temporary Redirect   (→ setup when incomplete)
POST /api/setup/finish 200     (skip / disabled AI)
GET / 200                      (dashboard after setup)
GET /virtual-screening|/medchem|/analysis|/settings|/setup 200
POST /api/research-os/project 200
GET /project/{id}/admet|lead-opt|research-os|publication|knowledge-engine 200
POST /api/analyse 200          (CCO → pipeline success)
GET /api/export/formats 200
GET /static/css/style.css 200
Restart: GET / 200 (no setup redirect)
```

---

## Results by area

### Build / bundle

| Check | Status | Notes |
|-------|--------|-------|
| EXE exists | **PASS** | `ChemistryCompanion.exe` |
| `_internal` present | **PASS** | |
| `setup_wizard.html` in bundle | **PASS** | Under `_internal/templates/` |
| RDKit/Open Babel/Vina natives | **PASS** | Logged at startup |

### First Run Experience (portable)

| Check | Status | Notes |
|-------|--------|-------|
| Fresh start requires setup | **PASS** | `GET /` → **307** `/setup` |
| Wizard page | **PASS** | `GET /setup` **200**, “Begin Setup” |
| Setup API | **PASS** | `/api/setup/status`, `/tools`, `/finish` |
| Tool detection | **PASS** | `/api/setup/tools` **200** |
| Skip → limited mode | **PASS** | Finish with `provider=disabled` |
| `.env` written next to EXE | **PASS** | Includes `CHEM_COMPANION_SETUP_COMPLETE=1` |
| Samples optional | **PASS** | Finish with `download_samples` (when requested) |
| Settings re-entry | **PASS** | `/settings` **200** contains Setup Wizard; `/setup` still **200** |
| After complete: no auto-wizard | **PASS** | Restart → `GET /` **200** (dashboard), not 307 to setup |

### Application smoke (post-setup)

| Check | Status |
|-------|--------|
| Dashboard | **PASS** |
| Virtual Screening | **PASS** |
| MedChem | **PASS** |
| Analysis page | **PASS** |
| Settings | **PASS** |
| ADMET / Lead Opt / Research OS / Publication / Knowledge (project-scoped) | **PASS** |
| HTMX analyse (ethanol) | **PASS** |
| Export formats | **PASS** |
| Static CSS | **PASS** |

### Runtime

| Check | Status | Notes |
|-------|--------|-------|
| SQLite DB at onedir root | **PASS** | `chemistry_companion.db` |
| File logging | **PASS** | `logs/chemistry_companion.log` |
| `Frozen=True` | **PASS** | Logged by `portable_entry` |
| Shutdown | **PASS** | Process terminated cleanly after tests |

---

## Known issues / residual notes

| ID | Severity | Note |
|----|----------|------|
| N1 | Low | Automated PowerShell helper used a function name that collided with alias `R` in one script draft; **HTTP logs still prove all smoke checks**. Future smoke scripts should avoid reserved aliases. |
| N2 | Info | Copying the entire onedir to another temp folder can fail if the path nesting is wrong; smoke was completed successfully **from `dist/ChemistryCompanion` directly**. |
| N3 | Info | Live AI Test Connection with production keys not re-run inside the portable EXE (covered in source FRE validation). |
| N4 | Info | **Installer not built** — blocked until this portable report; portable is green. |

None of these block promoting the portable build.

---

## Recommendation

```text
PORTABLE BUILD: PASS
NEXT STEP: Safe to build Windows installer (Inno Setup) from this onedir
DO NOT use an older onedir that predates FRE
```

### Suggested installer command (when authorized)

```powershell
# Only after portable_release_validation.md = PASS
.\installer\tools\InnoSetup6\ISCC.exe .\installer\ChemistryCompanion.iss
# → dist\installer\ChemistryCompanion-3.0.0-Setup.exe
```

---

## Summary

The PyInstaller **onedir** distribution was rebuilt with the validated FRE implementation and smoke-tested as a frozen process: first-run redirect, wizard, skip/configuration, module pages, analysis, export, static assets, DB/logs, and post-setup restart all succeeded. **No installer was produced in this phase.**
