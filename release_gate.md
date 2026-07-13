# Chemistry Companion 3.0.0 — Release Gate

| Field | Value |
|-------|-------|
| **Date** | 2026-07-13 |
| **Role** | Release Manager |
| **Candidate** | Chemistry Companion **3.0.0** |
| **Build number** | **20260713.2254** |
| **Git tag** | **`v3.0.0`** |
| **Primary artifact** | `ChemistryCompanion-3.0.0-Setup.exe` |

---

## Gate decision

# **PASS — READY FOR PUBLIC RELEASE**

All required release gates are satisfied. Residual risks are documented and non-critical for the validated distribution model.

---

## Official checklist

| # | Gate | Status |
|---|------|--------|
| 1 | Feature complete | **✓ PASS** |
| 2 | Workflow integrated | **✓ PASS** |
| 3 | Runtime validated | **✓ PASS** |
| 4 | Repository cleaned (publish surface) | **✓ PASS** |
| 5 | Dead code / mock product paths removed | **✓ PASS** |
| 6 | First Run Experience | **✓ PASS** |
| 7 | Portable build validated | **✓ PASS** |
| 8 | Windows installer validated | **✓ PASS** |
| 9 | Documentation updated | **✓ PASS** |
| 10 | No critical issues | **✓ PASS** |

---

## 1. Feature complete — PASS

Workbench modules available and wired:

- Analysis, Batch, Spectra, History, Exports  
- Docking workspace + visualization  
- PAMS protein assets  
- Virtual Screening, MedChem, ADMET, Lead Optimization  
- Research OS, Publication Assistant, Knowledge Engine  
- Optional AI with non-AI fallback  

**Evidence:** Product tree under `api/`, `services/`, `templates/`; module page loads in installer acceptance.

---

## 2. Workflow integrated — PASS

- Project-scoped routes (`/project/{id}/…`) for research modules  
- Campaign / portfolio / series / compound creation paths  
- Docking workspace → screening receptor dependency  
- Shared SQLite persistence under install/runtime root  

**Evidence:** `installer_validation.md` Scenarios 5–6 (corrected project IDs).

---

## 3. Runtime validated — PASS

| Check | Result |
|-------|--------|
| Frozen portable cold start | ~4.8 s to `/health` |
| FRE redirect | `/` → 307 `/setup` |
| Skip AI → Dashboard + analyse | PASS |
| Restart without wizard | PASS |
| Port conflict second instance | Clean exit code 1 |

**Evidence:** `portable_release_validation.md`, `final_release_audit.md`, `installer_validation.md`.

---

## 4. Repository cleaned (publication surface) — PASS

| Item | Status |
|------|--------|
| Secrets | `.env` gitignored; `.env.example` published |
| `dist/` | gitignored (build output, not source of truth) |
| License / credits / changelog at root | Present |
| Installer ships only EXE + `_internal` + LICENSE (+ optional `.env.example`) | Confirmed in ISS |
| Stale 1.0.0 Setup in `dist/installer/` | **Do not upload** (operator hygiene) |
| Local QA DB/logs under portable tree | Not in installer `[Files]` |

**Note:** Developer machine may still contain `node_modules/`, `outputs/`, backups — not part of the published Setup binary. Source release should exclude those via `.gitignore` / release packaging.

---

## 5. Dead code / mock product paths — PASS

| Item | Disposition |
|------|-------------|
| Virtual Screening mock affinities | **Removed** — real Vina pipeline |
| `mock_receptor.pdbqt` fallback | **Removed** |
| Application `TODO`/`FIXME` in core packages | None blocking |
| Test doubles / `unittest.mock` | Tests only — not shipped |

---

## 6. First Run Experience — PASS

| Check | Status |
|-------|--------|
| Wizard template shipped | PASS |
| First-run middleware redirect | PASS |
| Skip AI usable | PASS |
| OpenRouter config → `.env` | PASS |
| Key masking / no leak in status API | PASS |
| Wizard suppressed after completion | PASS |
| Settings re-entry path | Documented |

**Evidence:** `first_run_experience.md`, `fre_validation.md`, installer Scenarios 2–4, 7.

---

## 7. Portable build validated — PASS

| Check | Status |
|-------|--------|
| PyInstaller onedir `ChemistryCompanion.exe` | Present |
| Templates/static under `_internal` | PASS |
| Vina / Open Babel bundled | PASS |
| Smoke / rebuild validation report | `portable_release_validation.md` |

---

## 8. Windows installer validated — PASS

| Check | Status |
|-------|--------|
| `ChemistryCompanion-3.0.0-Setup.exe` | Built (~131.6 MB) |
| Fresh install | PASS |
| FRE + skip AI | PASS |
| Modules + research objects | PASS |
| Upgrade preserves DB/workspace/config | PASS |
| Uninstall removes program; keeps user data | PASS |
| Acceptance decision | **READY** (`installer_validation.md`) |

---

## 9. Documentation updated — PASS

| Document | Status |
|----------|--------|
| `README.md` | v3 install options |
| `CHANGELOG.md` | `[3.0.0] — 2026-07-13` |
| `CREDITS.md` | Author + stack |
| `LICENSE` | MIT 2026 |
| `citation.cff` | 3.0.0 / 2026-07-13 |
| `release_notes_v3.md` | Public notes |
| `release_summary.md` | Executive summary |
| `release_gate.md` | This gate |
| Packaging / FRE / installer reports | Present |

---

## 10. No critical issues — PASS

Critical = crash on install, no launch, data wipe on upgrade, FRE infinite loop, mock screening as product truth.

| Class | Open critical? |
|-------|----------------|
| Install / launch | **No** |
| FRE | **No** |
| Upgrade / data loss | **No** |
| Uninstall policy | **No** (data retained by design) |
| Screening truthfulness | **No** (real Vina) |

### Residual non-critical risks

| ID | Risk | Severity | Handling |
|----|------|----------|----------|
| R1 | Unsigned SmartScreen | Medium | Document “Run anyway” |
| R2 | Program Files write limits | Medium | Recommend current-user install |
| R3 | Browser before server ready | Low–Med | Document refresh |
| R4 | Console window | Low | Document leave open |
| R5 | CDN offline UI | Medium offline | Document online use |
| R6 | JSON `/api/analyze` bug | Low | HTMX UI path works |

---

## Version matrix

| Location | Value | Status |
|----------|-------|--------|
| `pyproject.toml` | 3.0.0 | ✓ |
| `api/__init__.py` | 3.0.0 | ✓ |
| `api/app.py` FastAPI + health | 3.0.0 | ✓ |
| `chemistry_companion.py` | 3.0.0 | ✓ |
| `services/first_run_service.py` | 3.0.0 | ✓ |
| `.env.example` | 3.0.0 | ✓ |
| `citation.cff` | 3.0.0 | ✓ |
| `installer/ChemistryCompanion.iss` | 3.0.0 | ✓ |
| Setup filename | 3.0.0 | ✓ |
| README badge | 3.0.0 | ✓ |

---

## License & credits gate

| Check | Status |
|-------|--------|
| `LICENSE` MIT © Aquib Belal 2026 | ✓ |
| Installer license page | ✓ |
| Packaged `LICENSE.txt` | ✓ |
| `CREDITS.md` | ✓ |
| `citation.cff` | ✓ |

---

## Installer gate (artifact)

| Check | Status |
|-------|--------|
| File present | ✓ |
| Version metadata 3.0.0 | ✓ |
| SHA-256 recorded in `release_summary.md` | ✓ |
| Do not ship 1.0.0 Setup | Operator note |

---

## Sign-off

```text
[x] Feature complete
[x] Workflow integrated
[x] Runtime validated
[x] Repository cleaned (publish surface)
[x] Dead code / mock product paths cleared
[x] First Run Experience
[x] Portable build validated
[x] Windows installer validated
[x] Documentation updated
[x] No critical issues
```

| Field | Value |
|-------|-------|
| Version | **3.0.0** |
| Build | **20260713.2254** |
| Release date | **2026-07-13** |
| Git tag | **`v3.0.0`** |

# READY FOR PUBLIC RELEASE

*Signed as Release Manager — Chemistry Companion 3.0.0 production gate.*
