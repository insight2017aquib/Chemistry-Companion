# Windows Packaging & Installer Implementation

**Document type:** Engineering implementation guide / technical handover  
**Audience:** Future AI coding agents, developers, maintainers, release engineers  
**Product:** Chemistry Companion  
**Public release version documented:** 3.0.0  
**Work window:** 2026-07-13 packaging through release-gate phases  
**Status at end of work:** Packaging complete; Windows installer complete; release gate **PASS / READY FOR PUBLIC RELEASE**

This document records **what was implemented**, **why**, **how it works**, and **how to maintain it**. It is not a product brochure and not a one-line changelog. Primary evidence sources (do not invent beyond these):

| Evidence | Path |
|----------|------|
| Packaging foundation | `packaging_foundation.md` |
| PyInstaller report | `pyinstaller_report.md` |
| Windows installer report | `windows_installer.md` |
| Clean-install QA | `release_validation_windows.md` |
| Release gate | `release_gate.md` |
| Release notes / summary | `release_notes_v3.md`, `final_release_summary.md` |
| Spec / ISS / entry | `chemistry_companion.spec`, `installer/ChemistryCompanion.iss`, `portable_entry.py`, `core/paths.py` |

---

## Overview

### Goal of the packaging effort

Convert a **feature-complete, repository-root application** into:

1. A **production Python package** (`pyproject.toml`, setuptools discovery, entry points, package data).  
2. A **portable Windows onedir binary** (PyInstaller, not onefile).  
3. A **professional Windows installer** (Inno Setup) with shortcuts, license, uninstaller, and registry metadata.  
4. Validated **clean-machine** behaviour (no system Python, no project venv).  
5. A **version-aligned 3.0.0** public release candidate with gate documentation.

### Preconditions (work already complete before packaging)

Packaging did **not** invent the application. Before packaging phases began, the project had already completed:

- Feature stabilization of the FastAPI research workbench  
- Workflow integration (analysis, docking workspace, research modules, PAMS, AI providers)  
- Repository cleanup and dead-code removal (see prior cleanup docs)  
- Release validation of application behaviour in development mode  

This document records **implementation of distribution**, not product feature design.

### What this document is not

- Not a marketing page  
- Not a plan for unfinished work presented as done  
- Not a substitute for reading the phase reports above when regenerating builds  

---

## Packaging Architecture

### Final architecture (three distribution modes)

```text
Source checkout (dev)
    │
    ├─► pip install -e .          → site-packages flat packages + chemistry_companion.py
    │
    ├─► PyInstaller onedir        → dist/ChemistryCompanion/
    │       ChemistryCompanion.exe
    │       _internal/   (sys._MEIPASS: code + templates + static + native libs)
    │       [writable at install root: db, logs, outputs, data/pams]
    │
    └─► Inno Setup                → dist/installer/ChemistryCompanion-3.0.0-Setup.exe
            installs onedir payload under {app}/
```

### Application entry points

| Mode | Entry | Behaviour |
|------|-------|-----------|
| Dev / pip server | `api.app:app` via `uvicorn`, or `python -m api` / `chemistry-companion-server` | `api/__main__.py` → Uvicorn string or object |
| Dev CLI | `chemistry_companion:main` / `chemistry-companion` | Top-level module `chemistry_companion.py` |
| Portable / installed | `portable_entry.py` frozen as `ChemistryCompanion.exe` | Bootstrap env → `ensure_runtime_directories` → `uvicorn.run(app)` **with app object** (not string import) |
| Thin launcher | `run.py` | Delegates to `api.__main__.main` (dev convenience) |

**Why object import for frozen Uvicorn:** String targets like `"api.app:app"` re-import modules under PyInstaller and break reliably; the portable entry imports `from api.app import app` then `uvicorn.run(app, ...)`.

### Package structure (flat multi-package)

The repository ships **top-level packages** (not a nested `src/chemistry_companion/` namespace):

```text
api/, core/, database/, docking_workflow/, exports/, llm/,
reports/, services/, spectra/, visualization/, templates/, static/, data/
+ chemistry_companion.py (py-module CLI)
```

Imports remain:

```python
from api.app import app
from core.config import get_settings
from services.analysis_service import AnalysisService
```

**Design decision:** Avoid a large import rewrite for packaging. Trade-off: flat names can pollute `site-packages` if installed via pip alongside other projects. Accepted for 3.0; optional future `src/` layout is deferred.

### Runtime resources vs package resources

| Kind | Location (frozen) | Location (dev) |
|------|-------------------|----------------|
| Read-only templates/static/sample data | `{exe_dir}/_internal/...` (`sys._MEIPASS`) | Repo root siblings of `core/` |
| Writable SQLite DB | `{exe_dir}/chemistry_companion.db` | Historically package-root / override |
| Outputs mount `/outputs` | `{exe_dir}/outputs` | Package-root `outputs/` or override |
| Logs | `{exe_dir}/logs/chemistry_companion.log` | Config-driven / portable bootstrap |
| PAMS protein store | `{exe_dir}/data/pams` (frozen default via runtime root) | `cwd/data/pams` historically |
| Docking workspaces | `{runtime}/outputs/docking_workspace` | `cwd/outputs/docking_workspace` historically |

Central API: **`core/paths.py`** (`package_root`, `install_root`, `templates_dir`, `static_dir`, `database_path`, `outputs_dir`, `pams_root`, `docking_workspace_root`, env overrides).

### Configuration loading

- **pydantic-settings** class `ChemistryCompanionSettings` in `core/config.py`  
- Env prefix: `CHEM_COMPANION_`, nested delimiter `__`  
- Optional `.env` (cwd-relative; portable entry `chdir`s to install root first)  
- Sample: `.env.example` shipped with wheel/onedir/installer  
- `.env` is **not** auto-created (user copies template for LLM keys)

### Static assets & templates

- Jinja2 templates: `templates/**/*.html` (37 HTML files + components)  
- Static: `static/css/*`, `static/js/*`, `static/custom.css|js`, empty `static/images/`  
- Mounted in `api/app.py` via `StaticFiles` at `/static` and `/outputs`  
- Primary page routes use `create_templates(templates_dir())` (package-safe)  
- **Known residual:** some route modules still construct Jinja with `Path("templates").absolute()` (CWD); under freeze that points at `{app}/templates` (missing) while real files live in `_internal/templates`. Canonical pages on `api.app` and `/project/{id}/…` use freeze-safe paths.

### Database initialization

- Lifespan in `api/app.py` calls `configure_database(database_url())`  
- SQLAlchemy `create_all` + `database/migrations.run_migrations`  
- Default frozen URL: `sqlite:///{install_root}/chemistry_companion.db`  
- Override: `CHEM_COMPANION_DB_PATH`

### Logging

- Portable entry configures console + `{install_root}/logs/chemistry_companion.log`  
- App also logs lifespan startup with DB URL  
- Installer creates empty `logs/` directory at install time  

### Resource discovery (native tools)

`portable_entry.py` sets (if found under install root / `_internal` / `openbabel/bin`):

| Env | Purpose |
|-----|---------|
| `BABEL_DATADIR` / `BABEL_LIBDIR` | Open Babel data + plugins |
| `VINA_BINARY` / `VINA_EXE` | AutoDock Vina CLI |
| `OBABEL_BINARY` / `OBABEL_EXE` | Open Babel CLI |

Docking code also has its own resolvers (`docking_workflow/vina_runner.py`, `protein_preparation.py`) for PATH/conda layouts.

### Version metadata

Public release version is **3.0.0**, unified across:

- `pyproject.toml`  
- `api/__init__.__version__`, FastAPI `version`, `/health`  
- `core.config` default `version`  
- `chemistry_companion.VERSION` (CLI)  
- `citation.cff`  
- Inno Setup `#define MyAppVersion "3.0.0"` → `ChemistryCompanion-3.0.0-Setup.exe`  

**Historical note:** Packaging foundation initially used **1.0.0** for the first wheel/onedir/installer experiments. Release-gate work re-aligned metadata and rebuilds to **3.0.0**. An older `ChemistryCompanion-1.0.0-Setup.exe` may still exist under `dist/installer/`; the canonical public artifact is **3.0.0**.

---

## Phase-by-Phase Implementation

### Phase 1 — Packaging Foundation

**Objective:** Make the project a real Python package without changing application architecture or behaviour.

**What was changed / created**

| Item | Role |
|------|------|
| `pyproject.toml` | setuptools build, metadata, deps, extras, entry points, package-data |
| `MANIFEST.in` | sdist include/exclude |
| `core/paths.py` | Package-safe path helpers (later freeze-aware) |
| `api/__main__.py` | `python -m api` / console server entry |
| `run.py` | Thin launcher (restored; had been accidental test content) |
| `data/__init__.py` | Allow packaging sample CSVs as package data |
| `packaging_foundation.md` | Phase report |

**Wiring (minimal behaviour-preserving path use)**

- `api/app.py` — templates, static, outputs mount, DB URL via `core.paths`  
- Selected routes/services (analysis, history, validation, benchmarks, docking, proteins, docking workspace) for sample data / outputs / PAMS / workspace roots  

**Design decisions**

1. **Flat package discovery** over `src/` layout (no import rewrite).  
2. **Package data** for `templates`, `static`, `data/*.csv|txt` only — not runtime `data/pams`.  
3. **Exclude** tests, scripts, archive, AutoDock-Vina source tree, node_modules, outputs.  
4. **Entry points:** `chemistry-companion` → CLI; `chemistry-companion-server` → web.  
5. Optional extras: `jupyter`, `protonation` (dimorphite-dl), `dev`, `full`.  

**Validation performed**

- setuptools discovery (~22 packages)  
- `pip install -e .`  
- Imports from a **non-repo cwd**  
- Wheel contents include templates/static/sample data  
- Config env override `CHEM_COMPANION_LOGGING__LEVEL`  

**Not in scope for Phase 1:** PyInstaller, Inno Setup, onefile, Docker, PyPI publish.

---

### Phase 2 — PyInstaller (onedir only)

**Objective:** Produce a self-contained Windows folder users can run without installing Python.

**Why onedir first (not onefile)**

- Faster startup and fewer “extract to temp” issues with large native scientific stacks  
- Easier inspection of missing templates/DLLs during bring-up  
- Onedir is the direct payload for the Inno Setup installer  
- Onefile deferred by design  

**Key files**

| File | Role |
|------|------|
| `portable_entry.py` | Freeze bootstrap + Uvicorn launch |
| `chemistry_companion.spec` | Analysis / EXE / COLLECT definition |
| `pyinstaller_report.md` | Phase report |

**Spec strategy**

1. **Analysis entry:** `portable_entry.py`  
2. **Datas:** `templates/`, `static/`, sample `data/*`, `.env.example`, `LICENSE`  
3. **`collect_all` / data / dynamic libs** for heavy packages: RDKit, Open Babel, Meeko, FastAPI stack, NumPy/Pandas/SciPy, Matplotlib, etc.  
4. **Explicit first-party `collect_submodules`:** api, core, services, docking_workflow, spectra, …  
5. **Hidden imports** for Uvicorn protocol workers, SQLAlchemy SQLite dialect, multipart, RDKit Chem entry points, Matplotlib Agg  
6. **Binaries:** `vina.exe`, `obabel.exe`, Open Babel `bin/` tree, `rdkit.libs` / `*.libs` DLLs, py2opsin JAR  
7. **`exclude_binaries=True` + COLLECT** → onedir layout  
8. **UPX disabled** (scientific DLLs often break under UPX)  
9. **Console EXE** kept for diagnostics  

**Runtime fixes (why required)**

| Problem | Fix |
|---------|-----|
| Writable paths must not live only under read-only `_MEIPASS` | `install_root()` = directory of EXE; DB/outputs/logs next to EXE |
| Open Babel needs data files | Bundle `openbabel/bin/data` + set `BABEL_DATADIR` |
| Vina/obabel not on PATH | Bundle binaries + set env in `portable_entry` |
| Uvicorn string app import fails when frozen | `uvicorn.run(app, …)` with imported app object |
| `/outputs` mount missing if directory absent | Create outputs before import / mkdir in app |
| Templates not found | Package as data under `_internal/templates` + `templates_dir()` → `_MEIPASS` |

**Dynamic imports handled**

- Spectra modules referenced via importlib in reports  
- FastAPI route modules collected via `collect_submodules`  
- Optional dimorphite / LLM providers may be absent; app degrades  

**Validation performed**

- Cold start ~10–12 s  
- Dashboard and research module pages (project-scoped) HTTP 200  
- HTMX analyse, export CSV/JSON, docking generate PDBQT  
- Bundled `vina.exe` / `obabel.exe` version checks  
- Dist size ~395 MB  

**Rebuild note:** After Virtual Screening mock-affinity removal (release-gate), onedir was **rebuilt** so the 3.0.0 installer payload includes the real docking path.

---

### Phase 3 — Windows Installer

**Objective:** Professional Windows distribution from the validated onedir payload.

**Technology:** Inno Setup **6.4.3** (local compiler under `installer/tools/InnoSetup6/` when system install was unavailable).

**Key files**

| File | Role |
|------|------|
| `installer/ChemistryCompanion.iss` | Installer script |
| `installer/build_installer.ps1` | Compile helper |
| `installer/assets/chemistry_companion.ico` | Multi-size icon |
| `installer/assets/make_icon.py` | Icon generator (Pillow) |
| `windows_installer.md` | Phase report |

**Installer layout / behaviour**

| Concern | Implementation |
|---------|----------------|
| Payload | Copies `ChemistryCompanion.exe` + entire `_internal\**` from `dist\ChemistryCompanion\` |
| Desktop shortcut | Task `desktopicon` → `{autodesktop}\Chemistry Companion.lnk` |
| Start Menu | Group “Chemistry Companion”: app + Uninstall |
| Icon | `ChemistryCompanion.ico` in `{app}`; Setup wizard icon from assets |
| License | MIT `LICENSE` as wizard LicenseFile; installed as `LICENSE.txt` |
| Version / publisher | AppVersion 3.0.0, Aquib Belal, VersionInfo* fields |
| Install directory | Default `{autopf}\Chemistry Companion` |
| Privileges | Prefer admin (Program Files); `PrivilegesRequiredOverridesAllowed=dialog commandline` enables `/CURRENTUSER` |
| Registry | `HKA\Software\Aquib Belal\Chemistry Companion` (InstallPath, Version, Publisher, DisplayName, UninstallString); Inno ARP key under Uninstall |
| Uninstaller | Standard Inno `unins000.exe`; `[UninstallDelete]` cleans logs/outputs/data/db/.env |
| Runtime dirs | Creates empty `logs`, `outputs`, `data`, `data\pams`, `outputs\docking_workspace` |
| Does **not** ship | Build-machine SQLite DB or validation outputs from the developer machine |
| Compile-time guard | ISPP `#if !FileExists(DistDir\exe)` fails compile if onedir missing |

**AppId (upgrade identity)** — keep constant across releases:

```text
{A7C3E8F1-2B4D-4E9A-9C1F-6D8E5A0B3C72}
```

**Validation performed**

- Silent install / upgrade (re-run Setup) / repair (re-run Setup) / uninstall  
- Desktop + Start Menu present then removed  
- Registry + ARP present then removed  
- Launch from installed EXE → Dashboard HTTP 200  

**Important:** Installing the app does **not** require modifying application Python code (installer wraps the onedir). Application path work was done in Phases 1–2 so the frozen app works when installed.

---

### Phase 4 — Windows Validation (clean machine simulation)

**Objective:** Prove the product runs without Python, venv, or developer tools.

**Method (actual)**

- Install `Setup.exe` with `/CURRENTUSER` into an isolated `%LOCALAPPDATA%\Programs\…` directory  
- Launch installed `ChemistryCompanion.exe` with PATH stripped of `.venv` / repo paths  
- Clear `VIRTUAL_ENV` / `PYTHONPATH` / `PYTHONHOME`  
- Exercise HTTP UI and selected APIs  
- Force stop and check port release / no crash dumps  

**Results (primary paths)**

| Area | Result |
|------|--------|
| Startup | PASS (~12 s), `Frozen=True` |
| DB init | PASS (`chemistry_companion.db` created) |
| Logging | PASS |
| Dashboard / VS / MedChem / project-scoped research modules | PASS |
| HTMX analysis / export / docking prep | PASS |
| Optional LLM without keys | PASS (error response, process stays up) |
| Shutdown | PASS |

**Known issues observed**

1. **Secondary** `GET /api/admet|lead-opt|publication|knowledge/` HTML routes → 500 under freeze: Jinja searches `{app}\templates` (missing); real templates under `{app}\_internal\templates`. **Primary UI** `/project/{id}/…` and pages served via `api.app` templates **work**.  
2. `.env` not auto-created (expected; copy from `.env.example`).  
3. CDN assets required for full UI chrome.  

Evidence: `release_validation_windows.md`.

---

### Phase 5 — Release Candidate

**Objective:** Align product version to **3.0.0**, clear remaining release blockers, document gate.

**What was done**

- Unified version strings to 3.0.0 (package, API, CLI, config, citation, ISS)  
- Root `CHANGELOG.md`, `CREDITS.md`, rewritten `README.md`  
- Removed Virtual Screening **mock random affinities**; wired real `prepare_docking_structure` + `run_vina`; screening start requires workspace receptor PDBQT  
- Rebuilt PyInstaller onedir and Inno Setup → **`ChemistryCompanion-3.0.0-Setup.exe`**  
- `release_gate.md`, `release_notes_v3.md`, `final_release_summary.md`  

**Release gate outcome:** **PASS — READY FOR PUBLIC RELEASE**

**Remaining risks (accepted, non-blocking)**

- CDN UI offline limitation  
- Secondary CWD template loaders  
- Unsigned Setup/EXE (SmartScreen)  
- Known JSON `/api/analyze` descriptor bug (HTMX path works)  
- Large install footprint (~400 MB)  
- Heuristic spectra scientific limitation  

---

## Runtime Dependency Strategy

| Dependency | How provided | Failure mode |
|------------|--------------|--------------|
| **Python runtime** | Embedded in PyInstaller onedir | N/A for installer users |
| **RDKit** | Collected into `_internal` + `rdkit.libs` DLLs | App fails cheminformatics hard if missing from build |
| **Open Babel** | Python package + `openbabel/bin` tools/data/plugins + `BABEL_DATADIR` | Docking prep fails with clear errors if data/binary missing |
| **AutoDock Vina** | Bundled `vina.exe`; env `VINA_BINARY` | Docking/screening jobs fail; UI may still load |
| **Meeko** | Python package in bundle | Fallback paths exist in ligand prep where coded |
| **Mol* / 3Dmol.js** | **Not vendored**; loaded from CDN in templates | 3D viewers need network |
| **AI providers** | HTTP APIs; keys via `.env` / env | Graceful degrade to templates / HTTP errors without crash |
| **dimorphite-dl** | Optional extra; not required | Protonation enumeration skipped |
| **JRE (OPSIN)** | System dependency for py2opsin JAR | IUPAC→SMILES may fail without Java |
| **SQLAlchemy/SQLite** | Bundled | DB created on first run |

**Graceful degradation principle (implemented where designed):** optional AI and optional protonation should not crash the process; core cheminformatics and docking depend on correctly bundled natives.

---

## Resource Management

### How resources are located after installation

```text
{app}/                              ← install_root() / directory of ChemistryCompanion.exe
  ChemistryCompanion.exe
  ChemistryCompanion.ico
  LICENSE.txt
  .env.example
  chemistry_companion.db            ← created at first run (writable)
  logs/chemistry_companion.log      ← created at first run
  outputs/                          ← created; mounted as /outputs
  data/pams/                        ← runtime protein assets
  _internal/                        ← sys._MEIPASS (package_root when frozen)
      templates/                    ← Jinja2 (primary app paths)
      static/css|js|...
      data/*.csv                    ← sample benchmarks
      openbabel/bin/...
      vina.exe, obabel.exe
      rdkit.libs/, numpy.libs/, ...
      Python + site-packages dump
```

### Algorithm (frozen)

1. `portable_entry` sets `install_root = dirname(sys.executable)`, `chdir` there.  
2. Default env for DB/outputs/PAMS/docking workspace under install root.  
3. Discover Babel/Vina/OBabel under install root and `_internal`.  
4. Configure file logging under `logs/`.  
5. `ensure_runtime_directories()`.  
6. Import `api.app` (uses `templates_dir()` / `static_dir()` → `_MEIPASS`).  
7. Uvicorn serves HTTP; lifespan initializes SQLite.  

### Configuration after install

- Optional: copy `{app}\.env.example` → `{app}\.env`  
- Overrides: `CHEM_COMPANION_*`, `VINA_BINARY`, `OBABEL_BINARY`, `BABEL_DATADIR`, `CHEM_COMPANION_HOST` / `PORT` / `OPEN_BROWSER`  

### Icons / images

- Installer/app shortcut icon: `installer/assets/chemistry_companion.ico` → `{app}\ChemistryCompanion.ico`  
- `static/images/` exists but had no marketing icons at packaging time  
- PyInstaller EXE may still use default console icon; shortcuts use the custom ICO  

---

## Installer Layout

### On disk after Setup (canonical)

```text
{app}/   e.g. C:\Program Files\Chemistry Companion\
              or %LOCALAPPDATA%\Programs\Chemistry Companion  (/CURRENTUSER)

  ChemistryCompanion.exe
  ChemistryCompanion.ico
  LICENSE.txt
  .env.example
  unins000.exe
  unins000.dat

  logs\                    (empty at install; populated at runtime)
  outputs\
  outputs\docking_workspace\
  data\
  data\pams\

  _internal\               (full PyInstaller payload — do not hand-edit)
      templates\
      static\
      data\
      openbabel\
      vina.exe
      obabel.exe
      ... (Python, RDKit, DLLs, …)

  chemistry_companion.db   (after first successful launch)
  .env                     (optional, user-created)
```

There is **no** separate top-level `templates/` or `static/` next to the EXE in the correct freeze layout; they live under `_internal/`. Any code that looks for `{cwd}/templates` is a defect relative to this layout (see Known Limitations).

---

## Validation Performed

| Layer | What | Outcome |
|-------|------|---------|
| Packaging foundation | Discovery, editable install, out-of-tree imports, wheel data | Pass |
| PyInstaller | Build, start, DB, logs, UI pages, analyse, export, docking prep, Vina/OBabel | Pass |
| Installer | Install, upgrade, repair, uninstall, shortcuts, registry, launch | Pass |
| Clean machine | No Python/venv; PATH sanitized; full mission UI checklist | Pass (primary paths) |
| Release gate | Version, docs, mock screening removed, rebuild 3.0.0 Setup | Pass |
| Application smoke (dev) | Prior feature/release validation before packaging | Assumed complete pre-phase |
| Workflow integration | Project-scoped research modules + analysis/export in frozen mode | Pass for UI/API used in QA |
| compileall | Main packages | Pass |

Automated clean QA tally (one run): **54 PASS / 5 WARNING / 0 FAIL** on primary mission paths (`release_validation_windows.md`).

---

## Known Limitations

| Item | Intentional? | Notes |
|------|--------------|-------|
| Onedir only (no onefile yet) | Yes | Simpler debug; installer uses onedir |
| CDN frontend (Tailwind, HTMX, Alpine, Plotly, 3Dmol) | Deferred | Offline UI incomplete without network |
| Secondary route Jinja CWD paths | Residual defect | Fix by migrating to `core.paths.templates_dir()` |
| Flat multi-package pip layout | Accepted | Avoided import rewrite |
| No Authenticode signing | Deferred | SmartScreen may warn |
| No auto `.env` | Yes | Security/privacy (keys) |
| JSON `/api/analyze` bug | Residual app bug | HTMX UI analysis works |
| Large footprint (~400 MB install) | Expected | RDKit/SciPy/Open Babel |
| Heuristic IR/NMR | Product design | Not DFT |
| OPSIN needs system JRE | External | JAR bundled only |
| PyInstaller console window | Yes for v3 | Diagnostics |

---

## Lessons Learned

1. **Onedir first is the right bring-up path** for a scientific stack with dozens of native DLLs and data files.  
2. **Resource loading must separate package root (`_MEIPASS`) from install root (EXE directory)**; writing SQLite into `_MEIPASS` is wrong.  
3. **Package-safe path helpers must be adopted before freezing**; `Path(__file__).parent` alone is insufficient once freezes and cwd-based code coexist.  
4. **Uvicorn must receive the app object when frozen**, not a reimportable string path.  
5. **Open Babel is not “import openbabel and done”** — format plugins and `BABEL_DATADIR` must be bundled and pointed at.  
6. **Installer must not re-pack developer machine state** (local DB, docking outputs); only EXE + `_internal`.  
7. **Compile-time vs install-time checks:** Inno Setup must not use relative DistDir checks at *runtime* InitializeSetup; ISPP compile-time `#if FileExists` is correct.  
8. **Mock data in “feature complete” modules is a release blocker** if the gate claims “no mock data” (Virtual Screening affinities were real-wired before 3.0.0 gate).  
9. **QA of packaging ≠ QA of every scientific edge case**; frozen UI pass does not replace docking regression science.  
10. **Version strings multiply** (CLI, FastAPI, health, ISS, citation); gate them all or users see 0.3 / 1.0 / 2.0 / 3.0 simultaneously.

---

## Guidance for Future AI Agents

### Assumptions that MUST remain true

1. **`portable_entry.py` is the frozen entry**; do not switch the frozen entry to `api.__main__` string Uvicorn without re-validating freeze.  
2. **`core.paths` freeze semantics:** `package_root()` = `_MEIPASS`; `install_root()` = EXE directory.  
3. **Primary HTML pages** must use `templates_dir()` / `create_templates(templates_dir())`, not `Path("templates")`.  
4. **Inno Setup payload** is always the **current** `dist/ChemistryCompanion` onedir.  
5. **AppId** `{A7C3E8F1-2B4D-4E9A-9C1F-6D8E5A0B3C72}` must stay stable for Windows upgrades.  
6. **Do not ship** `data/pams`, user DB, or `outputs/` contents inside the installer.  
7. **Virtual Screening** must not reintroduce random/fake affinities.  

### Files that should not be modified casually

| File | Risk if broken |
|------|----------------|
| `core/paths.py` | Wrong templates/static/DB under freeze or pip |
| `portable_entry.py` | App fails to start or finds wrong natives |
| `chemistry_companion.spec` | Missing RDKit/OB/Vina/templates |
| `installer/ChemistryCompanion.iss` | Broken installs/upgrades/uninstalls |
| `api/app.py` lifespan + mounts | DB/static/outputs regressions |
| Version fields (many files) | Inconsistent release metadata |

### How to safely update the installer

1. Bump `#define MyAppVersion` in `ChemistryCompanion.iss` (and `pyproject.toml` + other version sources).  
2. Keep **AppId** unchanged unless intentional product break.  
3. Rebuild onedir first (below).  
4. Compile ISS only when DistDir EXE exists.  
5. Re-run silent install + launch smoke on a clean directory.  

### How to update dependencies

1. Update `pyproject.toml` / `requirements.txt` in the **build venv**.  
2. Re-run application tests as appropriate.  
3. **Always rebuild PyInstaller** after dependency or native binary changes.  
4. Re-check `collect_all` list if new binary-heavy packages appear.  
5. Re-test docking prep + `vina --version` / `obabel -V` inside the new `_internal`.  

### How to regenerate portable + installer (canonical recipe)

```powershell
# From repository root, project venv active
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean chemistry_companion.spec

# Then
.\installer\tools\InnoSetup6\ISCC.exe .\installer\ChemistryCompanion.iss
# or: powershell -File .\installer\build_installer.ps1

# Outputs
#   dist\ChemistryCompanion\
#   dist\installer\ChemistryCompanion-<version>-Setup.exe
```

### Backward compatibility

- Windows upgrades: same AppId, `UsePreviousAppDir=yes`, `ignoreversion` on files.  
- SQLite: migrations remain idempotent (`database/migrations.py`).  
- Env prefix `CHEM_COMPANION_` is the public config contract.  
- Do not rename console scripts without release notes.  

### How future releases (e.g. 3.1) should build on this

1. Fix residual CWD Jinja loaders → `core.paths.templates_dir()`.  
2. Optionally vendor CDN assets under `static/vendor/` if offline is a goal.  
3. Authenticode-sign Setup + EXE.  
4. Consider onefile only after onedir remains green.  
5. Optional `src/` package rename as a **separate** PR with full import migration.  
6. Keep this document updated when packaging architecture changes.  

---

## Files Modified / Created

Complete table of packaging-related implementation (application feature modules not listed unless packaging-touched).

| File | Purpose | Reason for modification / creation |
|------|---------|-------------------------------------|
| `pyproject.toml` | Package metadata, deps, entry points, package-data | Enable pip packaging and discovery |
| `MANIFEST.in` | sdist rules | Ensure templates/static/sample data in sdist |
| `core/paths.py` | Package/freeze path resolution | Avoid hardcoded absolute paths; frozen vs writable roots |
| `api/__main__.py` | `python -m api` / server console entry | Proper application entry point |
| `run.py` | Thin web launcher | Restore launcher; point at `api.__main__` |
| `data/__init__.py` | Package marker for sample data | Wheel inclusion of CSVs |
| `api/app.py` | Use paths; mkdir outputs; version | Freeze-safe resources; mount `/outputs`; version metadata |
| `api/routes/analysis.py` | `templates_dir()` | Package-safe templates |
| `api/routes/history.py` | `templates_dir()` | Package-safe templates |
| `api/routes/validation.py` | package/sample/outputs paths | Package-safe resources |
| `api/routes/benchmarks.py` | sample/outputs paths | Package-safe resources |
| `api/routes/docking.py` | `outputs_dir()` | Package-safe outputs |
| `api/routes/proteins.py` | `pams_root()` | Writable PAMS location |
| `services/docking_workspace_service.py` | `docking_workspace_root()` | Writable docking jobs |
| `core/config.py` | Default version field | Align with release version |
| `portable_entry.py` | Frozen app entry | Bootstrap env, natives, logging, Uvicorn |
| `chemistry_companion.spec` | PyInstaller onedir definition | Bundle code, data, natives |
| `installer/ChemistryCompanion.iss` | Inno Setup script | Windows installer product |
| `installer/build_installer.ps1` | Build helper | Compile ISS reliably |
| `installer/assets/make_icon.py` | Icon generation | Multi-size ICO for Setup/shortcuts |
| `installer/assets/chemistry_companion.ico` | App/Setup icon | Branding for installer and shortcuts |
| `chemistry_companion.py` | CLI VERSION | Version alignment for release |
| `api/__init__.py` | `__version__` | Version alignment |
| `citation.cff` | Citation version/date | Version alignment |
| `services/screening_service.py` | Real Vina screening path | Remove mock affinities before public release |
| `api/routes/virtual_screening.py` | Receptor from workspace heavy_data | Remove mock_receptor fallback |
| `llm/docking_explainer.py` | Prompt wording | Remove “Mocked” label |
| `README.md` | Product + install docs | v3 install channels |
| `CHANGELOG.md` | Version history | Release documentation |
| `CREDITS.md` | Third-party credits | Release documentation |
| `packaging_foundation.md` | Phase 1 report | Evidence |
| `pyinstaller_report.md` | Phase 2 report | Evidence |
| `windows_installer.md` | Phase 3 report | Evidence |
| `release_validation_windows.md` | Phase 4 report | Evidence |
| `release_gate.md` / `release_notes_v3.md` / `final_release_summary.md` | Phase 5 | Gate + public notes |
| `docs/changelog/win_setup_file.md` | This handover | Canonical packaging reference |
| `dist/ChemistryCompanion/**` | Built onedir | Generated artifact |
| `dist/installer/ChemistryCompanion-3.0.0-Setup.exe` | Built Setup | Generated artifact |
| `installer/tools/InnoSetup6/**` | Local ISCC (optional bootstrap) | Compile environment when system Inno unavailable |

---

## Summary

| Topic | Status |
|-------|--------|
| **Current release status** | 3.0.0 release gate **PASS** — ready for public release |
| **Packaging status** | Production `pyproject.toml` + freeze-safe paths + onedir PyInstaller **complete** |
| **Installer status** | Inno Setup professional installer **complete**; clean-machine validation **pass** |
| **Canonical public Setup** | `dist/installer/ChemistryCompanion-3.0.0-Setup.exe` |
| **Canonical portable** | `dist/ChemistryCompanion/` |

### Recommended next steps for Version 3.1

1. Migrate remaining route modules’ Jinja loaders to `core.paths.templates_dir()` (eliminate secondary `/api/...` template 500s).  
2. Authenticode-sign `ChemistryCompanion-*.exe` Setup and app EXE.  
3. Optionally vendor CDN JS/CSS under `static/vendor/` for offline labs.  
4. Fix JSON `POST /api/analyze` descriptor serialization.  
5. Slim PyInstaller excludes (test modules pulled via aggressive `collect_all`) if size becomes a problem.  
6. Update this document if architecture changes (entry point, AppId, layout).  

---

*End of engineering handover. Prefer phase reports for raw validation logs; prefer this file for architecture, maintenance, and agent guidance.*
