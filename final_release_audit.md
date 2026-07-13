# Final Release Audit — Chemistry Companion 3.0.0 (Windows)

| Field | Value |
|-------|-------|
| **Role** | Release Manager |
| **Date** | 2026-07-13 |
| **Ship artifact** | `dist/installer/ChemistryCompanion-3.0.0-Setup.exe` (~132 MB) |
| **Prior gate** | Installer acceptance → **READY** (`installer_validation.md`) |
| **Scope** | Quality audit only — no features, no architecture redesign |
| **Focus** | Application startup + anything that would hurt first downloads |

---

## Executive decision

### CONDITIONAL GO — ship with documented install guidance

**Application startup is verified healthy** on a clean writable runtime.

There are **no crash-level startup defects** in the portable/installer binary path under a user-writable install directory (the path acceptance already proved).

There **are** polish and packaging issues that will reduce perceived quality for some users tomorrow. None require a science/feature rebuild. One packaging default (**Program Files + user data next to EXE**) is the highest residual risk if users take the installer defaults without elevation for later writes.

| Gate | Result |
|------|--------|
| Cold start succeeds | **PASS** (~4.8 s to `/health`) |
| FRE surfaces on first run | **PASS** (`/` → 307 `/setup`, wizard HTML OK) |
| Health / version | **PASS** (`version: 3.0.0`, visualization available) |
| Installer payload clean (no QA `.env`/DB) | **PASS** (by ISS design) |
| Default Program Files writability | **RISK** (see H1) |
| Code signing / SmartScreen | **RISK** (unsigned) |
| First-open browser timing | **WARN** (browser before listen) |

**If you can only publish one message with the binary:**  
*Install for the current user (or under `%LOCALAPPDATA%\Programs\…`), wait ~10 seconds on first launch for the black console + browser, complete or skip Setup, then work.*

---

## Application startup — verified

### Method

- Binary: `dist/ChemistryCompanion/ChemistryCompanion.exe` (same onedir the Setup embeds)
- Fresh runtime dir under `%TEMP%` (no prior `.env` / marker)
- `CHEM_COMPANION_OPEN_BROWSER=0`, host `127.0.0.1`, port `8810`

### Results

| Check | Result | Measured |
|-------|--------|----------|
| Process stays up | **PASS** | Does not exit on success path |
| `/health` ready | **PASS** | **~4808 ms** cold start |
| `/setup` (FRE) | **PASS** | HTTP 200, ~29 KB, “Begin Setup” present |
| `/` first visit | **PASS** | HTTP **307** → setup (first-run middleware) |
| Health payload | **PASS** | `status=healthy`, `version=3.0.0`, visualization OK |
| Logs written | **PASS** | `logs/chemistry_companion.log` under runtime |
| DB created | **PASS** | SQLite file created under runtime |
| Templates / static | **PASS** | Present under `_internal` (logged at boot) |
| Vina / Open Babel discovery | **PASS** | Logged as set under `_internal` |
| Second instance same port | **Handled** | Exit code **1**, clear WinError 10048 bind error (no zombie second server) |

### Startup chain (as shipped)

1. `ChemistryCompanion.exe` → `portable_entry.main()`
2. `chdir(install_root)`, set `CHEM_COMPANION_*` defaults, discover Vina/obabel/BABEL_DATADIR
3. Create logs / outputs / DB parent dirs
4. Import FastAPI app + Uvicorn
5. Optionally open browser (`CHEM_COMPANION_OPEN_BROWSER` default **1**)
6. Bind `127.0.0.1:8000` (unless overridden)

**Conclusion:** Startup path is production-viable for a normal user-writable install. First listen is on the order of **~5 seconds** on this machine (cold); slower machines / AV first-scan may take longer.

---

## Issues that reduce release quality

Severity: **H** = may fail or block real users · **M** = noticeable polish · **L** = operational / packaging hygiene

### H1 — Default install directory may be non-writable for user data

| | |
|--|--|
| **What** | Inno default: `DefaultDirName={autopf}\Chemistry Companion` (typically `C:\Program Files\…`) with `PrivilegesRequired=admin`. App stores `.env`, SQLite, logs, outputs under **install root** next to the EXE. |
| **Why it hurts** | After install, users usually run the app **without** elevation. Writing config/DB under Program Files often fails. FRE path validation can report “Not writable,” which is recoverable but a poor default for tomorrow’s downloads. |
| **Acceptance gap** | Installer QA used `/CURRENTUSER` under `%LOCALAPPDATA%\Programs\…` (always writable). |
| **Mitigation without redesign** | Publish “install for me only” / LocalAppData instructions; or change next Setup default to `{localappdata}\Programs\{#MyAppName}` + `PrivilegesRequired=lowest`. Wizard already validates path writability. |
| **Ship impact** | **Conditional** — do not market “just Next-Next-Finish into Program Files” without path guidance. |

### H2 — Binaries are not Authenticode-signed

| | |
|--|--|
| **Evidence** | `Get-AuthenticodeSignature` → **NotSigned** on both Setup and EXE |
| **Why it hurts** | SmartScreen / “Windows protected your PC” friction; some orgs block unsigned installers. |
| **Mitigation** | Sign with a code-signing cert before wide distribution; document “More info → Run anyway” for early adopters. |
| **Ship impact** | Expected for many indie first releases; expect support noise. |

### M1 — Browser opens before the server is listening

| | |
|--|--|
| **Where** | `portable_entry.py`: `webbrowser.open(url)` **then** `uvicorn.run(...)` |
| **Why it hurts** | Users often see a failed page / connection refused for several seconds on first launch, then must refresh. Cold start ~5s makes this common. |
| **Mitigation** | Defer browser open until bind succeeds (small packaging fix; not done in this audit). Document: “If the page fails, wait and refresh.” |

### M2 — Console window always visible

| | |
|--|--|
| **Evidence** | PE subsystem **3 (CONSOLE)**; `chemistry_companion.spec` has `console=True` |
| **Why it hurts** | Double-click → black console with logs. Feels like a developer tool, not a finished desktop app. |
| **Mitigation** | Intentional for support/troubleshooting; productize later with `console=False` + tray/log UI. For v3.0, mention “leave the console open while you work.” |

### M3 — Port 8000 already in use

| | |
|--|--|
| **Evidence** | Second instance exits **1** with `[Errno 10048]` after startup log |
| **Why it hurts** | Double-click twice: second instance dies; first may still work. No friendly dialog. |
| **Mitigation** | Document single-instance expectation; future: pick free port or focus existing browser tab. |

### L1 — Stale Setup binary next to the release

| | |
|--|--|
| **Evidence** | `dist/installer/ChemistryCompanion-1.0.0-Setup.exe` still present alongside 3.0.0 |
| **Why it hurts** | Easy to upload the wrong file if packaging the whole folder. |
| **Mitigation** | Publish **only** `ChemistryCompanion-3.0.0-Setup.exe`. |

### L2 — Portable onedir working tree is polluted (dev only)

| | |
|--|--|
| **Evidence** | `dist/ChemistryCompanion/` contains `.env`, `.cc_setup_complete`, `chemistry_companion.db`, logs, outputs |
| **Installer** | **Does not ship these** — `[Files]` only EXE + `_internal` + icon + LICENSE + optional `.env.example` |
| **Mitigation** | Clean before any future rebuild so onedir zips stay first-run clean. |

### L3 — EXE has no embedded icon (`icon=None` in spec)

| | |
|--|--|
| **Note** | Installer places `ChemistryCompanion.ico` and uses it for Start Menu/Desktop shortcuts. Taskbar for console host may look generic. |
| **Mitigation** | Rebuild later with icon in the spec (requires PyInstaller rebuild — out of scope for this audit). |

### L4 — Live AI not re-proved in this audit

| | |
|--|--|
| **Note** | Installer acceptance covered invalid-key + `.env` storage. Real OpenRouter key not required for startup gate. |

---

## What is solid for public download

- Setup installs program payload only; user data not wiped on uninstall (by design).
- First Run Experience auto-redirect works; skip AI works; dashboard reachable after setup.
- Version string consistent: app **3.0.0**, health **3.0.0**, Setup filename **3.0.0**.
- Binds to **127.0.0.1** by default (not exposed on LAN).
- Core tool discovery (Vina, Open Babel data) logged and present under `_internal`.
- Installer acceptance scenarios 1–9 already **READY**.

---

## Pre-publish checklist (tomorrow morning)

1. Upload **only** `ChemistryCompanion-3.0.0-Setup.exe` (not the 1.0.0 file, not the whole `dist/` tree).
2. Release notes bullet:
   - Prefer **current-user** install or a writable folder (avoid Program Files if you do not want to run elevated).
   - First launch: console window is normal; wait ~10 s; refresh browser if needed.
   - Uninstall keeps research data (`.env`, database, logs, outputs).
3. Optional but high value: code-sign Setup + EXE.
4. Optional small packaging follow-ups (post-3.0.0 or hot Setup rebuild):
   - DefaultDir → `%LOCALAPPDATA%\Programs\Chemistry Companion`
   - Open browser only after Uvicorn is listening
5. Do **not** rebuild PyInstaller for this audit’s findings unless you choose to fix M1/M2/H1 in code.

---

## Application startup — sign-off

| Item | Status |
|------|--------|
| Starts without crash (writable runtime) | **PASS** |
| Becomes HTTP-ready | **PASS** (~5 s cold) |
| First-run wizard reachable | **PASS** |
| Logs + DB initialize | **PASS** |
| Suitable for public download *with install guidance* | **YES** |

---

## Final statement

**Application startup is release-quality** for the validated install model (user-writable directory).

**Residual quality reducers** for tomorrow’s users: unsigned SmartScreen friction, console window, browser-before-ready race, and **Program Files default vs local writes**.

### Release Manager decision

# SHIP — CONDITIONAL GO

Ship `ChemistryCompanion-3.0.0-Setup.exe` with clear install-location and first-launch notes.  
Do **not** treat an unguided “default admin → Program Files → double-click” path as fully proven.

*No feature work and no architecture redesign performed in this audit.*
