# Chemistry Companion — Packaging Foundation

**Date:** 2026-07-13  
**Phase objective:** Prepare the project for packaging (not installers, not PyInstaller).  
**Package name:** `chemistry-companion`  
**Canonical version:** `1.0.0`  
**License:** MIT (Aquib Belal, 2026)

---

## 1. Executive summary

Chemistry Companion is now installable as a standard Python distribution via `pyproject.toml` (setuptools). Verification completed for:

| Check | Result |
|-------|--------|
| Package discovery | 22 packages found |
| Metadata (name, version, author, license, deps, extras) | OK |
| Console entry points | `chemistry-companion`, `chemistry-companion-server` |
| Wheel / sdist build | `chemistry_companion-1.0.0` builds successfully |
| Templates / static / sample data in wheel | Included (38 / 9 / 4 files) |
| Imports from outside repository root | OK (editable install) |
| Resource resolution via package-safe helpers | OK (`core.paths`) |
| Configuration (`CHEM_COMPANION_*`, `.env`) | OK |

**Not in scope for this phase:** PyInstaller, NSIS/MSI installers, single-file EXE, Docker image, PyPI publish.

---

## 2. Package structure

### 2.1 Layout (flat multi-package)

The project uses a **flat repository root** — multiple top-level packages ship side-by-side (not a single nested `chemistry_companion/` namespace). Imports remain as they are in development:

```text
from api.app import app
from core.config import get_settings
from services.analysis_service import AnalysisService
```

```text
Chemistry Companion/                  # repository root
├── pyproject.toml                    # NEW — production packaging config
├── MANIFEST.in                       # NEW — sdist inclusions / exclusions
├── packaging_foundation.md           # THIS DOCUMENT
├── chemistry_companion.py            # CLI module (py-module)
├── run.py                            # thin web launcher → api.__main__
├── requirements.txt                  # legacy pin list (kept for launchers)
├── LICENSE / README.md / citation.cff
├── .env.example
│
├── api/                              # FastAPI app + routes + schemas
│   ├── __main__.py                   # NEW — python -m api / server entry
│   ├── app.py
│   ├── templating.py
│   ├── routes/
│   └── schemas/
├── core/                             # cheminformatics + config + PAMS
│   ├── paths.py                      # NEW — package-safe path helpers
│   ├── config.py
│   ├── pipeline.py
│   ├── pams/
│   └── pams_integrations/
├── database/                         # SQLAlchemy models + migrations
├── docking_workflow/                 # Vina / prep / interactions
├── exports/                          # CSV / JSON / Excel exporters
├── llm/                              # LLM clients / docking explainer
├── reports/                          # report export helpers
├── services/                         # application services (incl. services/ai)
├── spectra/                          # IR / ¹H / ¹³C predictors
├── visualization/                    # 2D/3D viewers
├── templates/                        # Jinja2 HTML (packaged data)
├── static/                           # CSS / JS (packaged data)
├── data/                             # sample CSVs (packaged; not PAMS runtime)
│
├── tests/                            # excluded from distribution
├── scripts/                          # dev tooling — excluded
├── archive/                          # excluded
├── AutoDock-Vina/                    # vendored C++ tree — excluded / gitignored
├── node_modules/                     # JS test deps only — excluded
├── outputs/ / output/ / backups/     # runtime artifacts — excluded
└── docs/                             # not packaged as code
```

### 2.2 Discovered packages (setuptools)

```text
api, api.routes, api.schemas
core, core.pams, core.pams.sources, core.pams_integrations
data
database
docking_workflow
exports, exports.excel, exports.exporters, exports.schemas
llm
reports
services, services.ai
spectra
static
templates
visualization
```

**Plus py-module:** `chemistry_companion` (CLI).

### 2.3 What is intentionally excluded from the wheel

| Path | Reason |
|------|--------|
| `tests/`, `scripts/`, `archive/` | Dev-only |
| `AutoDock-Vina/` | Large C++ source tree; not a Python dep |
| `node_modules/` | Frontend audit tooling only |
| `outputs/`, `output/`, `backups/` | Runtime / user data |
| `graphify-out/` | Dev graph artifacts |
| `data/pams/`, `data/pams_cache/` | Runtime protein asset store (user-writable) |
| Root debug scripts (`debug_*.py`, probes, logs) | Not library surface |

---

## 3. Resource inventory

### 3.1 Packaged read-only resources

| Resource | Location | Count / notes | Loader |
|----------|----------|---------------|--------|
| Jinja2 templates | `templates/**/*.html` | 37 HTML (+ package `__init__`) | `core.paths.templates_dir()` → Jinja2 `FileSystemLoader` |
| Template components | `templates/components/` | Shared HTMX partials | Same |
| CSS | `static/css/`, `static/custom.css` | 3 files | Starlette `StaticFiles` at `/static` |
| JavaScript | `static/js/`, `static/custom.js` | 5 files (`app.js`, `shell.js`, `utils.js`, `workbench.js`, `custom.js`) | `/static` |
| Images / icons | `static/images/` | Empty in tree; package-data globs ready | `/static` |
| Sample benchmarks | `data/benchmark_molecules.csv`, `data/spectra_benchmark.csv` | Bundled sample sets | `core.paths.sample_data_dir()` |
| Sample SMILES list | `data/smiles_input.txt` | Quick batch input | Same |

**Wheel verification:** templates 38, static 9, data 4 members included.

### 3.2 Runtime writable resources (not packaged content)

| Resource | Default location | Override env |
|----------|------------------|--------------|
| SQLite DB | `<package_root>/chemistry_companion.db` | `CHEM_COMPANION_DB_PATH` |
| Outputs mount | `<package_root>/outputs` | `CHEM_COMPANION_OUTPUTS_DIR` |
| Docking workspaces | `<cwd>/outputs/docking_workspace` | `CHEM_COMPANION_DOCKING_WORKSPACE_DIR` |
| PAMS protein store | `<cwd>/data/pams` | `CHEM_COMPANION_PAMS_DIR` |
| Config settings dirs | `output/` (+ images/exports/logs/batch) via `core.config` | `CHEM_COMPANION_DIRECTORIES__OUTPUT_DIR` |
| Runtime base | process cwd | `CHEM_COMPANION_RUNTIME_DIR` |

### 3.3 External / non-Python resources

| Resource | How resolved | Notes |
|----------|--------------|-------|
| AutoDock Vina CLI | `VINA_BINARY` / `VINA_EXE`, PATH, conda `Library/bin`, pypi `vina` tree | Native binary — **not** in the wheel |
| Open Babel CLI (`obabel`) | `OBABEL_BINARY` / `OBABEL_EXE`, venv Scripts, conda | From `openbabel-wheel` or system |
| ChimeraX | `CHEM_COMPANION_EXTERNAL_TOOLS__CHIMERA_EXECUTABLE` | Optional |
| CDN assets (Tailwind, HTMX, Plotly, Alpine) | Loaded from CDN in `templates/base.html` | Offline packaging risk |
| JRE | Required at runtime by `py2opsin` | Not declared as a Python dep |
| LLM API keys | `.env` / process env | Never packaged |

### 3.4 Database initialization

1. App lifespan (`api.app`) calls `configure_database(database_url())`.
2. `database.models.configure_database` creates the SQLAlchemy engine, `Base.metadata.create_all`, then runs idempotent `database.migrations.run_migrations`.
3. Default URL: `sqlite:///<package_root>/chemistry_companion.db` (historical path preserved).
4. FastAPI dependencies use `get_db()` session factory.

---

## 4. Entry points

### 4.1 Declared console scripts (`pyproject.toml`)

| Script | Target | Purpose |
|--------|--------|---------|
| `chemistry-companion` | `chemistry_companion:main` | CLI toolkit (analyse, batch, spectra, export, demo, version, …) |
| `chemistry-companion-server` | `api.__main__:main` | Uvicorn web server |

### 4.2 Module / launcher equivalents

| Command | Equivalent |
|---------|------------|
| `python -m api` | Web server (`api.__main__`) |
| `python run.py` | Thin wrapper → `api.__main__.main` |
| `uvicorn api.app:app --host 127.0.0.1 --port 8000` | Legacy launchers (`Start_Chemistry_Companion.bat`, `CC_LAUNCHER.ps1`) |
| `python chemistry_companion.py version` | Direct CLI module |

### 4.3 Server host/port

| Variable | Default |
|----------|---------|
| `CHEM_COMPANION_HOST` | `127.0.0.1` |
| `CHEM_COMPANION_PORT` | `8000` |

### 4.4 ASGI application object

```text
api.app:app
```

This remains the stable target for Uvicorn, Hypercorn, and future process managers.

---

## 5. Dependency audit

### 5.1 Runtime (core) — from `[project.dependencies]`

| Category | Packages |
|----------|----------|
| Cheminformatics | `rdkit`, `openbabel-wheel`, `pandas`, `numpy`, `scipy`, `pubchempy`, `py2opsin`, `gemmi` |
| Docking prep | `meeko`, `py3Dmol` |
| Export / plots | `openpyxl`, `matplotlib`, `seaborn`, `tabulate` |
| Web | `fastapi`, `uvicorn`, `Jinja2`, `python-multipart`, `SQLAlchemy`, `aiosqlite`, `pydantic`, `pydantic-settings` |
| Utilities | `python-dotenv`, `requests`, `colorama` |

### 5.2 Optional extras

| Extra | Contents | Use |
|-------|----------|-----|
| `jupyter` | `jupyter`, `nbformat` | Tutorials / notebooks |
| `protonation` | `dimorphite-dl` | Optional ligand protonation enumeration (gracefully skipped if missing) |
| `dev` | `pytest`, `pytest-asyncio`, `httpx`, plus jupyter stack | Tests and notebooks |
| `full` | all of the above | Convenience meta-extra |

### 5.3 Install examples

```bash
# Editable development (recommended while developing)
pip install -e ".[dev]"

# Runtime only
pip install .

# With optional protonation
pip install ".[protonation]"
```

Legacy path (launchers still use this):

```bash
pip install -r requirements.txt
```

### 5.4 Dependency notes / risks

| Item | Severity | Detail |
|------|----------|--------|
| `rdkit` / `openbabel-wheel` wheels | Medium | Platform-specific wheels; conda-forge often more reliable for docking stacks |
| AutoDock Vina CLI | High for docking | Not a declared Python dependency; must be on PATH or `VINA_BINARY` |
| `py2opsin` → JRE | Medium | IUPAC→SMILES needs a Java runtime |
| `meeko` | Low | Used with graceful OpenBabel fallback |
| `dimorphite-dl` | Low | Optional; commented out of `requirements.txt`, available as extra |
| Duplicate `python-dotenv` lines in `requirements.txt` | Low | Harmless; prefer `pyproject.toml` as source of truth going forward |
| CDN JS (Tailwind/HTMX/Plotly) | Medium for offline | Not vendored; requires network for full UI |

---

## 6. Metadata verification

| Field | Value | Source |
|-------|-------|--------|
| Project name | `chemistry-companion` | `pyproject.toml` |
| Version | `1.0.0` | `pyproject.toml` (canonical) |
| Author | Aquib Belal | `pyproject.toml`, `LICENSE`, `citation.cff` |
| License | MIT | `LICENSE` + package classifiers |
| Requires Python | `>=3.10` | `pyproject.toml` / README badge |
| Homepage / repo | github.com/aquibbelal/chemistry-companion | `pyproject.toml`, `citation.cff` |
| Description | Integrated toolkit for molecular analysis, heuristic spectral prediction, and docking preparation | `pyproject.toml` |

### 6.1 Version string inventory (drift)

| Location | Version observed | Status |
|----------|------------------|--------|
| `pyproject.toml` | **1.0.0** | **Canonical** |
| `citation.cff` | 1.0.0 | Aligned |
| `api/__init__.__version__` | 1.0.0 | Aligned |
| `api.app` FastAPI `version=` | 1.0.0 | Aligned (this phase) |
| `core.config` default `version` | 1.0.0 | Aligned (this phase) |
| `chemistry_companion.VERSION` (CLI banner) | **0.3.0** | **Drift** — recommend sync next release |

---

## 7. Package discovery & install verification

### 7.1 Discovery

```text
setuptools find_packages → 22 packages
wheel top_level.txt → api, chemistry_companion, core, data, database,
  docking_workflow, exports, llm, reports, services, spectra,
  static, templates, visualization
```

### 7.2 Imports outside the repository root

Verified with an editable install while cwd was a temporary directory outside the repo:

- `from core.config import get_settings` ✓  
- `from core.paths import templates_dir, static_dir, sample_data_dir` ✓  
- `from core.pipeline import ChemistryPipeline` ✓  
- `from api.app import app` (176 routes registered) ✓  
- `import chemistry_companion` + console script `chemistry-companion version` ✓  
- `importlib.resources.files("templates"|"static"|"data")` ✓  

### 7.3 Configuration loading

| Mechanism | Status |
|-----------|--------|
| `pydantic-settings` with prefix `CHEM_COMPANION_` | Working |
| Nested delimiter `__` (e.g. `CHEM_COMPANION_LOGGING__LEVEL=DEBUG`) | Working |
| `.env` via `env_file=".env"` on settings model | Working (relative to process cwd) |
| `get_settings()` LRU cache + `reset_settings_cache()` | Working |
| `save_to_file` / `load_from_file` JSON | Working |

**Note:** `env_file=".env"` is cwd-relative. After install, users should either place `.env` in the launch cwd or rely on real environment variables.

---

## 8. Package-safe resource loading

### 8.1 New module: `core/paths.py`

Central helpers avoid hardcoded absolute machine paths:

| Helper | Role |
|--------|------|
| `package_root()` | Root containing `api`, `templates`, `static`, … |
| `templates_dir()` / `static_dir()` / `sample_data_dir()` | Packaged resources |
| `database_path()` / `database_url()` | SQLite location |
| `outputs_dir()` | Generated artifacts + static mount |
| `pams_root()` / `docking_workspace_root()` | Writable stores (cwd-based defaults) |
| `runtime_root()` / `ensure_runtime_directories()` | Writable base + mkdir helper |

### 8.2 Call sites updated (behaviour-preserving)

- `api/app.py` — templates, static, outputs mount, DB URL  
- `api/routes/analysis.py`, `history.py` — templates  
- `api/routes/validation.py`, `benchmarks.py`, `docking.py` — sample data / outputs  
- `api/routes/proteins.py` — PAMS root  
- `services/docking_workspace_service.py` — docking workspace root  

Defaults match historical locations (package-root DB/outputs; cwd-based PAMS/docking workspaces).

### 8.3 Remaining path patterns (documented tech debt)

| Pattern | Where | Risk |
|---------|-------|------|
| `sys.path.insert(...)` | CLI, some routes, spectra | Unnecessary after install; keep for source checkout |
| Dual `output/` vs `outputs/` | `core.config` vs docking/API | Confusing dual roots |
| Dynamic import of `run_spectra_validation` | validation route | Module may be gitignored / not packaged |
| Dynamic import of `scripts.run_tool_comparison` | benchmarks route | `scripts/` excluded from distribution |
| CDN URLs in templates | `base.html` | Offline / air-gapped failure |

---

## 9. Packaging risks

### 9.1 High

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Flat multi-package install pollutes site-packages** | Top-level names `api`, `core`, `services`, `static`, `templates` can collide with other packages | Long-term: migrate to `src/chemistry_companion/` single namespace (import rewrite — out of scope for this phase) |
| **Writable DB under package_root** | Non-editable install may try to write SQLite into site-packages | Set `CHEM_COMPANION_DB_PATH` (or future user-data default) for production installs |
| **Native Vina binary not packaged** | Docking run fails without external CLI | Document install via conda-forge or `VINA_BINARY`; future optional binary bundling for installers only |
| **Benchmark/validation routes import non-packaged scripts** | `scripts/*` and `run_spectra_validation` not in wheel | Move shared logic into `core`/`services` or ship scripts as package modules |

### 9.2 Medium

| Risk | Impact | Mitigation |
|------|--------|------------|
| **CLI version drift (`0.3.0` vs `1.0.0`)** | Confusing version reporting | Single `__version__` imported from package metadata |
| **`.gitignore` ignores `data/` and `*.csv`** | Fresh clones may lack sample CSVs if not force-tracked | Track sample files explicitly; keep runtime `data/pams` ignored |
| **CDN frontend deps** | UI broken offline | Vendor minified assets under `static/vendor/` for offline builds |
| **`openbabel-wheel` / RDKit platform issues** | Install failures on some OS/arch | Document conda alternative in README |
| **`env_file=".env"` cwd coupling** | Settings miss secrets when launched from another directory | Prefer process env; or resolve `.env` next to runtime root |
| **Outputs static mount only if directory exists** | Fresh install may not serve `/outputs` until first write creates the tree | Call `ensure_runtime_directories()` at startup (optional next step) |

### 9.3 Low

| Risk | Impact | Mitigation |
|------|--------|------------|
| Empty `static/images/` | No app icons yet | Add icons when branding assets exist |
| `requirements.txt` vs `pyproject.toml` dual source | Drift over time | Generate one from the other or document pyproject as SoT |
| Large repo noise (`outputs`, logs, backups) | Bloats checkout, not the wheel | Already excluded; keep cleaning |
| `tests` package has `__init__` but is excluded | Fine for setuptools | Keep exclude list |

---

## 10. Recommendations (next packaging steps)

### 10.1 Before any installer / PyInstaller work

1. **Single version source** — read `importlib.metadata.version("chemistry-companion")` in CLI and config.  
2. **User-data defaults for installed (non-editable) mode** — DB/outputs under platform user data dir when not running from a source tree.  
3. **Fold validation/benchmark helpers into packaged modules** so web routes do not depend on `scripts/` or root debug files.  
4. **Vendor or pin CDN assets** if offline desktop packaging is planned.  
5. **Document external binaries** (Vina, optional ChimeraX, JRE for OPSIN) in a short `docs/INSTALL.md`.  
6. **Keep `pip install -e .` as the primary dev workflow**; keep BAT/PS1 launchers as convenience wrappers that call `chemistry-companion-server` once installed.

### 10.2 Optional structural upgrade (later; architecture-impacting)

Move to:

```text
src/chemistry_companion/
  api/
  core/
  ...
  templates/
  static/
```

This eliminates site-packages name collisions but requires coordinated import rewrites. **Do not do this as part of freeze/release unless planned as its own PR.**

### 10.3 Explicitly deferred

- PyInstaller / cx_Freeze / Nuitka one-file or onedir builds  
- Windows MSI / NSIS / Inno Setup  
- Code signing  
- PyPI publish pipeline  
- Conda-forge feedstock  

---

## 11. Files added or changed in this phase

### Added

| File | Purpose |
|------|---------|
| `pyproject.toml` | Production package metadata, deps, extras, entry points, package-data |
| `MANIFEST.in` | sdist include/exclude rules |
| `core/paths.py` | Package-safe path resolution |
| `api/__main__.py` | `python -m api` / server console entry |
| `data/__init__.py` | Make sample data a package for wheel inclusion |
| `packaging_foundation.md` | This report |
| `run.py` | Restored thin launcher (was accidentally test-content) |

### Updated (resource wiring only; no feature changes)

| File | Change |
|------|--------|
| `api/app.py` | Use `core.paths`; FastAPI version → 1.0.0 |
| `api/routes/analysis.py` | `templates_dir()` |
| `api/routes/history.py` | `templates_dir()` |
| `api/routes/validation.py` | package-safe paths |
| `api/routes/benchmarks.py` | package-safe paths |
| `api/routes/docking.py` | `outputs_dir()` |
| `api/routes/proteins.py` | `pams_root()` |
| `services/docking_workspace_service.py` | `docking_workspace_root()` |
| `core/config.py` | Default version → 1.0.0 |

---

## 12. Quick validation checklist

```bash
# From a clean venv
pip install -e ".[dev]"

# Metadata
python -c "import importlib.metadata as m; print(m.version('chemistry-companion'))"

# Outside the repo root
cd $TEMP   # or any non-repo directory
python -c "from api.app import app; from core.paths import templates_dir; print(app.title, templates_dir().exists())"
chemistry-companion version
# chemistry-companion-server   # starts web UI on 127.0.0.1:8000

# Build artifacts (optional)
python -m build
# → dist/chemistry_companion-1.0.0-py3-none-any.whl
```

---

## 13. Conclusion

Chemistry Companion is **packaging-ready** as a setuptools-based Python project:

- Production `pyproject.toml` with metadata, dependencies, optional extras, and entry points  
- Resource packaging for templates, static assets, and sample data  
- Package-safe path helpers with env overrides for writable locations  
- Verified discovery, wheel build, and out-of-tree imports  

Remaining work is **release hygiene** (version single-sourcing, user-data defaults, script packaging for validation routes) and later **installer** work — not foundation packaging.
