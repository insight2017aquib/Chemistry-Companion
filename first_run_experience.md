# First Run Experience (FRE) — Implementation

**Feature:** Setup Wizard / First Run Experience  
**Version context:** Chemistry Companion 3.0  
**Date:** 2026-07-13  

---

## Architecture

The FRE is a **web multi-step wizard** integrated into the existing FastAPI + Jinja2 application. It does not introduce a separate desktop framework.

```text
Browser  →  GET /setup  →  templates/setup_wizard.html (Alpine.js steps)
                │
                ├─ GET  /api/setup/status
                ├─ POST /api/setup/ensure-dirs
                ├─ POST /api/setup/validate-paths
                ├─ GET  /api/setup/tools
                ├─ POST /api/setup/test-ai
                ├─ POST /api/setup/samples
                ├─ POST /api/setup/finish
                └─ POST /api/setup/validate

Middleware: if setup incomplete → redirect HTML GETs to /setup
Services: services/first_run_service.py
Config: writes/merges .env at config root + .cc_setup_complete marker
```

### When the wizard runs automatically

`services.first_run_service.needs_first_run()` is true when:

1. No `.env` file exists at the config root, **or**
2. `CHEM_COMPANION_SETUP_COMPLETE` is not set / marker file `.cc_setup_complete` is missing  

After Finish or Skip, both marker and `CHEM_COMPANION_SETUP_COMPLETE=1` are written. The wizard does **not** auto-show again unless the user opens **Settings → Setup Wizard** (`/setup?force=1`; `/setup` is always allowed).

### Config root

| Mode | Location |
|------|----------|
| Dev | Package / repo root (`package_root()`) |
| Frozen portable/installer | Directory of `ChemistryCompanion.exe` |
| Override | `CHEM_COMPANION_RUNTIME_DIR` (set by `portable_entry.py`) |

---

## Flow

| Step | UI | Backend |
|------|-----|---------|
| 1 Welcome | Capabilities, Begin / Skip | — |
| 2 Workspace | DB / outputs / logs / workspace paths | `ensure-dirs` |
| 3 AI provider | OpenRouter, OpenAI, Groq, Ollama, Disable | status catalog |
| 4 API keys | Provider-specific fields + Test Connection | `test-ai` |
| 5 Scientific tools | RDKit, Open Babel, Vina, Java, OPSIN | `tools` |
| 6 Optional | Sample datasets, docs link | `samples` on finish |
| 7 Summary | Review + Finish | — |
| 8 Storage | Create/merge `.env` | `finish` → `write_env_config` |
| 9 Validation | Writable paths, config readable, AI status | `final_validation` |
| 10 Launch | Redirect to `/` | — |

**Skip:** creates minimal `.env` with `AI_PROVIDER=disabled` and marks setup complete (limited functionality, no re-prompt).

**Existing `.env`:** finish without confirmation returns `needs_confirmation`; user must confirm overwrite/merge.

---

## Files modified / created

| File | Role |
|------|------|
| **`services/first_run_service.py`** | **New** — detection, tools, AI test, `.env` merge, samples, validation |
| **`api/routes/first_run.py`** | **New** — `/api/setup/*` endpoints |
| **`templates/setup_wizard.html`** | **New** — multi-step wizard UI |
| `api/app.py` | Register router, `/setup` page, first-run middleware |
| `templates/settings.html` | Setup Wizard card + AI not configured banner |
| `templates/base.html` | Settings nav link; footer v3.0 |
| `.env.example` | Document FRE / AI / path keys |
| `first_run_experience.md` | This document |

Scientific workflows, docking, spectra, and research modules were **not** redesigned.

---

## New components

### Service (`first_run_service`)

- `needs_first_run()`, `default_paths()`, `ensure_dirs()`, `validate_paths()`
- `detect_scientific_tools()` — RDKit import, Open Babel, Vina CLI, Java, py2opsin
- `test_ai_connection()` — OpenRouter / OpenAI / Groq chat completion smoke, Ollama `/api/tags`
- `write_env_config()` — merge keys, mask-safe logging, setup marker
- `copy_sample_datasets()` — copies bundled CSVs to `outputs/samples`
- `final_validation()`, `current_config_public()` — masked keys only

### API routes

Prefix: `/api/setup`

Friendly error messages only; no stack traces in responses. API keys accepted only for validation HTTP calls to the selected provider.

### UI

Standalone wizard page (extends no base nav chrome) so first-time users are not dropped into a half-configured shell. Uses existing Tailwind CDN + design tokens consistent with the app.

---

## Settings integration

- **Settings → Setup Wizard** button → `/setup?force=1`
- AI provider section points users to the wizard instead of “edit `.env` manually”
- Banner when no providers have keys: *AI Provider Not Configured* + Configure AI link

---

## Configuration storage

`.env` fields populated by the wizard (empty strings allowed):

```text
APP_VERSION=
CHEM_COMPANION_SETUP_COMPLETE=
AI_PROVIDER=
LLM_PROVIDER=
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=
OPENROUTER_MODEL=
OPENAI_API_KEY=
OPENAI_MODEL=
GROQ_API_KEY=
GROQ_MODEL=
OLLAMA_HOST=
OLLAMA_PORT=
OLLAMA_MODEL=
DATABASE_PATH=
OUTPUT_PATH=
LOG_PATH=
WORKSPACE_PATH=
CHEM_COMPANION_DB_PATH=
CHEM_COMPANION_OUTPUTS_DIR=
CHEM_COMPANION_LOG_PATH=
CHEM_COMPANION_RUNTIME_DIR=
CHEM_COMPANION_DOCKING_WORKSPACE_DIR=
```

Also preserves any pre-existing keys (e.g. `GEMINI_API_KEY`, `VINA_BINARY`) on merge.

---

## Security

| Rule | Implementation |
|------|----------------|
| Never log API keys | Logger records provider name/path only |
| Mask keys in UI status | `_mask_secret()` in public status payload |
| Password inputs | `type="password"` for key fields |
| No stack traces to client | Broad `except` → friendly message |
| Keys only for provider validation | `test_ai` posts to provider endpoints only |

---

## Validation performed

| Check | Result |
|-------|--------|
| `needs_first_run` before/after write | Pass |
| `.env` contains required keys | Pass |
| Tool detection returns RDKit/OB/Vina/Java/OPSIN | Pass (dev env) |
| `POST /api/setup/test-ai` disabled | Pass |
| `GET /setup` renders Welcome | Pass |
| Merge preserves existing secret keys | Pass |
| Isolated `CHEM_COMPANION_RUNTIME_DIR` write | Pass |

---

## Known limitations

1. **OpenAI / Ollama** are configured via `.env` for FRE; core `llm_utils` registry historically focused on Groq/DeepSeek/OpenRouter/Gemini — OpenAI key is stored for future/compatible use; full routing may still use existing provider manager for in-app explanations until those providers are fully registered in `core/llm_utils.py`.  
2. **Middleware** only redirects **GET** HTML navigations; API clients are not blocked (by design).  
3. **Test Connection** requires network (or local Ollama).  
4. **Wizard does not re-bundle** PyInstaller; new templates/routes ship with the next portable/installer rebuild.  
5. Completing setup in a **dev repo** writes `.env` at the package root (expected).  

---

## Guidance for maintainers

- To force wizard again: delete `.cc_setup_complete` and set `CHEM_COMPANION_SETUP_COMPLETE=0`, or use Settings → Setup Wizard.  
- Do not instruct end users to hand-edit `.env`; point them to the wizard.  
- After changing FRE files, rebuild onedir/installer if shipping Windows builds.  
- Keep API responses free of exception text.  

---

## Summary

Chemistry Companion now includes a commercial-style **First Run Experience** that creates configuration automatically, validates workspace and AI settings, detects scientific tools without blocking, and re-opens from Settings. Existing scientific workflows and packaging architecture are preserved.
