# Chemistry Companion — PyInstaller Onedir Report

**Date:** 2026-07-13  
**Build type:** **onedir only** (not onefile)  
**PyInstaller:** 6.21.0  
**Python:** 3.14.0 (Windows 11, 64-bit)  
**Spec:** `chemistry_companion.spec`  
**Entry:** `portable_entry.py`  
**Output:** `dist/ChemistryCompanion/ChemistryCompanion.exe`

---

## 1. Executive summary

A production-quality **portable onedir** build was produced and validated.

| Check | Result |
|-------|--------|
| Spec + hidden imports + datas/binaries | Built successfully |
| Executable starts HTTP server | OK (~10 s cold start) |
| Database initialization | OK (`chemistry_companion.db` next to EXE) |
| Logging | OK (`logs/chemistry_companion.log`) |
| Templates + static CSS/JS | Served 200 |
| Dashboard / Virtual Screening / MedChem | 200 |
| ADMET / Lead Opt / Research OS / Publication / Knowledge Engine | 200 (project-scoped URLs) |
| HTMX molecular analysis pipeline | 200 |
| Export (CSV/JSON) | 200 |
| Docking prep (RDKit + Open Babel / Meeko) | 200 PDBQT generated |
| AutoDock Vina CLI bundled | `vina.exe` v1.2.5 responds |
| Open Babel CLI bundled | `obabel.exe` 3.1.0 responds |

**Dist size:** ~395 MB  
**EXE size:** ~47.5 MB (bootloader + PKG; bulk of assets in `_internal/`)

---

## 2. How to build

```powershell
# From repository root, with project venv active
.\.venv\Scripts\python.exe -m pip install "pyinstaller>=6.0"
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean chemistry_companion.spec
```

Run portable app:

```powershell
cd dist\ChemistryCompanion
.\ChemistryCompanion.exe
# Browser opens http://127.0.0.1:8000 by default
```

Useful environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `CHEM_COMPANION_HOST` | `127.0.0.1` | Bind address |
| `CHEM_COMPANION_PORT` | `8000` | Bind port |
| `CHEM_COMPANION_OPEN_BROWSER` | `1` | Open browser on start (`0` to disable) |
| `CHEM_COMPANION_DB_PATH` | `<install>/chemistry_companion.db` | SQLite path |
| `CHEM_COMPANION_OUTPUTS_DIR` | `<install>/outputs` | Generated files |
| `VINA_BINARY` / `OBABEL_BINARY` | Auto-detected in `_internal` | Override native tools |
| `BABEL_DATADIR` | Auto-detected Open Babel data | Force field / atom types |

---

## 3. Files bundled

### 3.1 Application resources

| Category | Destination in bundle | Notes |
|----------|----------------------|-------|
| Jinja2 templates | `_internal/templates/**` | 37 HTML pages + components |
| Static CSS | `_internal/static/css/*`, `custom.css` | design-system + style |
| Static JS | `_internal/static/js/*`, `custom.js` | app, shell, utils, workbench |
| Icons / images | `_internal/static/images/` | Directory present; no icon assets yet |
| Fonts | — | None shipped under `static/` (UI uses CDN/system fonts) |
| Sample data | `_internal/data/*.csv`, `smiles_input.txt` | Benchmarks / samples |
| Config sample | `_internal/.env.example` | User copies to `.env` next to EXE |
| License | `_internal/LICENSE` | MIT |

### 3.2 Native / scientific binaries

| Binary / tree | Destination | Role |
|---------------|-------------|------|
| `vina.exe` | `_internal/vina.exe` | AutoDock Vina 1.2.5 CLI |
| `obabel.exe` (+ OB tools) | `_internal/` and `openbabel/bin/` | Open Babel CLI |
| `openbabel/bin/*.obf` | Format plugins | Structure conversion |
| `openbabel/bin/data/*` | Force fields, atom types | Required for docking prep |
| `openbabel-3.dll` | Bundled with openbabel | Native library |
| `rdkit.libs/*.dll` | `_internal/rdkit.libs/` | RDKit native deps |
| `numpy.libs`, `pandas.libs`, `scipy.libs`, `openbabel_wheel.libs` | `_internal/*` | Wheel shared libs |
| `py2opsin/*.jar` | `_internal/py2opsin/` | OPSIN IUPAC→SMILES (needs system JRE) |

### 3.3 Python packages (via `collect_all` / analysis)

Includes first-party packages:

`api`, `core`, `database`, `docking_workflow`, `exports`, `llm`, `reports`, `services` (+ `services.ai`), `spectra`, `visualization`, `data`, `static`, `templates`

And third-party (non-exhaustive): RDKit, Open Babel, Meeko, FastAPI, Starlette, Uvicorn, SQLAlchemy, Pydantic, Jinja2, Matplotlib (Agg), Seaborn, NumPy, Pandas, SciPy, Gemmi, py3Dmol, PubChemPy, py2opsin, openpyxl, requests, python-dotenv, colorama, aiosqlite, multipart, h11/httptools/websockets.

### 3.4 Dist layout

```text
dist/ChemistryCompanion/
├── ChemistryCompanion.exe          # launcher
├── chemistry_companion.db          # created at first run (writable)
├── logs/chemistry_companion.log    # created at first run
├── outputs/                        # docking, exports, mounts as /outputs
├── data/pams/                      # protein asset store (writable)
└── _internal/
    ├── templates/
    ├── static/
    ├── data/
    ├── openbabel/
    ├── rdkit.libs/
    ├── vina.exe
    ├── obabel.exe
    └── … Python + site-packages …
```

---

## 4. Hidden imports

### 4.1 Strategy

1. **`collect_all(pkg)`** for binary-heavy / plugin packages (RDKit, Open Babel, FastAPI, SQLAlchemy, Matplotlib, NumPy, …).  
2. **`collect_submodules(pkg)`** for all first-party packages (routes, services, spectra dynamic loaders).  
3. **Explicit list** for Uvicorn protocol workers, SQLAlchemy SQLite dialect, multipart, RDKit Chem entry points, Meeko, Matplotlib Agg, spectra modules.

### 4.2 Explicit critical set (excerpt)

```text
uvicorn.logging / loops.auto / protocols.http.* / lifespan.on
sqlalchemy.dialects.sqlite[.pysqlite|.aiosqlite]
aiosqlite, sqlite3
multipart, python_multipart
fastapi, starlette.staticfiles, starlette.templating
pydantic, pydantic_settings
rdkit.Chem, AllChem, Descriptors, Draw, rdDepictor, …
openbabel, openbabel.pybel
meeko
spectra.ir_predictor, proton_nmr, carbon_nmr, functional_group_detector
matplotlib.backends.backend_agg
py2opsin, dotenv, requests
```

### 4.3 Build-time hidden-import notes

| Item | Severity | Note |
|------|----------|------|
| `meeko.molecule_preparation` | Low | ERROR during analysis — wrong submodule name; Meeko still works (docking prep succeeded via package API) |
| `scipy.special._cdflib` | Low | Optional SciPy internal |
| `MySQLdb` | Low | SQLAlchemy optional dialect; app uses SQLite only |
| `rdkit.sping.WX` | Low | Optional Wx backend not installed |
| `matplotlib.tests` / pandas numba / torch | Low | Test/optional backends skipped |
| `pubchempy` / `aiofiles` collect_data | Low | Not packages with data trees |

Full PyInstaller missing-module dump: `build/chemistry_companion/warn-chemistry_companion.txt` (~794 lines; mostly Unix-only / optional / test modules — **not blocking** on Windows).

---

## 5. Freeze-aware runtime behaviour

### 5.1 Path resolution (`core/paths.py`)

| Mode | Resources (`package_root`) | Writable (`install_root` / runtime) |
|------|----------------------------|-------------------------------------|
| Dev / pip | Repo / site-packages parent | CWD / package root (historical) |
| **Frozen** | `sys._MEIPASS` (`_internal`) | Directory of `ChemistryCompanion.exe` |

### 5.2 Entry bootstrap (`portable_entry.py`)

1. `chdir` to install root  
2. Set runtime env defaults (DB, outputs, PAMS, docking workspace)  
3. Discover `BABEL_DATADIR`, `VINA_BINARY`, `OBABEL_BINARY`  
4. Configure console + file logging  
5. `ensure_runtime_directories()` **before** importing `api.app` (so `/outputs` mounts)  
6. `uvicorn.run(app, …)` with the **app object** (not a string import — required under PyInstaller)

---

## 6. Validation results

Validation run on port **8765** with `CHEM_COMPANION_OPEN_BROWSER=0`.

### 6.1 Startup / infrastructure

| Item | Result |
|------|--------|
| Process start | PID alive; server ready ~10 s |
| Log line | `Frozen=True`, templates/static exist, Vina/OBabel/Babel data set |
| DB | `sqlite:///…/dist/ChemistryCompanion/chemistry_companion.db` created |
| Lifespan | `Chemistry Companion started (db=…)` |
| Logs | `logs/chemistry_companion.log` |

### 6.2 UI pages

| Page | URL | Status | Notes |
|------|-----|--------|-------|
| Dashboard | `/` | **200** | Full shell + dashboard |
| Virtual Screening | `/virtual-screening` | **200** | Title “Virtual Screening” |
| MedChem | `/medchem` | **200** | Workbench template |
| ADMET | `/project/{id}/admet` | **200** | After project create |
| Lead Optimization | `/project/{id}/lead-opt` | **200** | |
| Research OS | `/project/{id}/research-os` | **200** | |
| Publication | `/project/{id}/publication` | **200** | |
| Knowledge Engine | `/project/{id}/knowledge-engine` | **200** | |
| Projects picker | `/projects` | **200** | |
| Legacy `/admet`, `/lead-opt`, … | redirect **307** → `/projects` | Expected app design |

Project used: `proj_3d15cb84e3` (“Portable Validation Project”) via `POST /api/research-os/project`.

### 6.3 Static assets

| Asset | Status |
|-------|--------|
| `/static/css/style.css` | 200 |
| `/static/css/design-system.css` | 200 |
| `/static/js/app.js` | 200 |

### 6.4 Analysis / exports / docking

| Capability | Result |
|------------|--------|
| HTMX `POST /api/analyse` (`input_text=c1ccccc1`) | **200**, ~9 KB HTML results |
| `GET /api/export/formats` | **200** csv/json/xlsx |
| `POST /api/export` CSV/JSON | **200** |
| `POST /api/docking/generate` (ethanol) | **200**, PDBQT written under `outputs/docking/` |
| `vina.exe --version` | AutoDock Vina v1.2.5 |
| `obabel.exe -V` | Open Babel 3.1.0 |

### 6.5 Known app-level issue (not packaging-specific)

`POST /api/analyze` (JSON) returns **500** with `Analysis failed: get` because `api/routes/analysis.py` calls `.get()` on a descriptor **model object**, not a dict.  
Reproduced identically with `TestClient` in the venv (non-frozen). **HTMX UI analysis path works** and is the primary GUI path.

---

## 7. Runtime issues observed

| Issue | Impact | Mitigation / status |
|-------|--------|---------------------|
| Cold start ~10 s | First launch slower (matplotlib font cache, RDKit load) | Expected; subsequent launches faster |
| Matplotlib font cache on first run | One-time warning in log | Harmless |
| CDN front-end (Tailwind, HTMX, Alpine, Plotly, 3Dmol/Mol*) | UI needs network for full interactivity | Documented offline risk |
| `py2opsin` JAR needs system JRE | IUPAC name resolution may fail without Java | Install JRE or avoid IUPAC inputs |
| Bundle size ~395 MB | Large portable folder | Expected with RDKit/SciPy; slim later by excluding tests/unused scipy |

No freeze-time crash; no missing template/static; no DB or logging failures during validation.

---

## 8. Warnings (build)

| Warning | Action needed? |
|---------|----------------|
| Failed collect `rdkit.sping.WX` | No — unused Wx path |
| RDKit pilfonts metrics | No — cosmetic |
| Matplotlib/pandas/scipy test or optional modules | No |
| `collect_data_files` skip for pubchempy/aiofiles | No |
| Hidden import `meeko.molecule_preparation` not found | No — docking prep still OK |
| Large `warn-*.txt` “missing module” list (posix, pwd, torch, MySQLdb, …) | No for Windows onedir |

---

## 9. Remaining packaging risks

### High

| Risk | Detail | Recommendation |
|------|--------|----------------|
| **CDN dependency for UI chrome** | Tailwind/HTMX/Alpine/Plotly/3Dmol loaded from CDN | Vendor minified assets under `static/vendor/` for true offline |
| **Large onedir footprint** | ~395 MB includes SciPy test modules / Jupyter spill from collect_all | Tighten `excludes` / avoid collecting `*.tests` submodules |
| **External JRE for OPSIN** | JAR bundled, runtime Java not | Document or ship JRE separately (installer phase) |

### Medium

| Risk | Detail | Recommendation |
|------|--------|----------------|
| **Mol\* / 3Dmol.js not offline** | Viewers inject CDN scripts | Optional local 3Dmol bundle |
| **`api/routes/research_os.py` templates path** | Uses `Path("templates").absolute()` (cwd) for *router* templates | Migrate to `core.paths.templates_dir()` (app page routes already safe) |
| **Validation/benchmark routes** | May import unpackaged `scripts/` / root helpers | Move helpers into `core` before relying on those buttons in portable mode |
| **JSON `/api/analyze` bug** | Descriptor object `.get` misuse | Fix route to use model attributes / `asdict` (app bug, both frozen & dev) |
| **No application icon** | `icon=None` in EXE | Add `.ico` when branding assets exist |
| **Antivirus false positives** | Unsigned PyInstaller EXE | Code-sign in installer phase |

### Low

| Risk | Detail |
|------|--------|
| Console window visible | Intentional for diagnostics; switch to windowed later |
| Flat multi-package site layout inside `_internal` | Fine for onedir; still a long-term namespace concern for pip installs |
| Dual `output/` vs `outputs/` naming | Unchanged app behaviour |

---

## 10. Files added / modified for this phase

| File | Role |
|------|------|
| `chemistry_companion.spec` | Onedir Analysis / EXE / COLLECT definition |
| `portable_entry.py` | Freeze bootstrap + Uvicorn launch |
| `core/paths.py` | Frozen-aware package/install/runtime paths |
| `api/app.py` | Ensure `outputs` dir exists so `/outputs` mounts |
| `pyinstaller_report.md` | This document |
| `pyinstaller_build.log` | Full build log (local artifact) |
| `dist/ChemistryCompanion/` | Portable distribution |

---

## 11. Validation checklist (copy/paste)

```text
[x] Build onedir with chemistry_companion.spec
[x] ChemistryCompanion.exe starts
[x] DB file created next to EXE
[x] Log file written under logs/
[x] Dashboard 200
[x] Virtual Screening 200
[x] MedChem 200
[x] ADMET (project-scoped) 200
[x] Lead Optimization (project-scoped) 200
[x] Research OS (project-scoped) 200
[x] Publication (project-scoped) 200
[x] Knowledge Engine (project-scoped) 200
[x] Static CSS/JS 200
[x] HTMX analyse 200
[x] Export formats + CSV/JSON 200
[x] Docking generate PDBQT 200
[x] vina.exe / obabel.exe present and executable
[ ] Offline UI without CDN (not in scope)
[ ] Onefile build (explicitly deferred)
```

---

## 12. Conclusion

Chemistry Companion has a **working portable onedir PyInstaller distribution**. Core web workflows, database init, logging, static assets, molecular analysis (HTMX), exports, and docking preparation with bundled Vina/Open Babel all operate from `dist/ChemistryCompanion/`.

Next release-engineering steps (optional): vendor CDN assets for offline use, slim the bundle, fix the JSON analyze route, add an app icon, then consider **installer packaging** or **onefile** only after offline UI is solid.
