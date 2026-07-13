# Chemistry Companion 3.0.0 — Release Summary

**Role:** Release Manager  
**Date:** 2026-07-13  
**Decision:** **READY FOR PUBLIC RELEASE**

---

## Identity

| Field | Value |
|-------|-------|
| **Product** | Chemistry Companion |
| **Version number** | **3.0.0** |
| **Build number** | **20260713.2254** |
| **Release date** | **2026-07-13** |
| **Git tag recommendation** | **`v3.0.0`** |
| **License** | MIT (`LICENSE`) |
| **Author / publisher** | Aquib Belal |
| **Primary ship file** | `dist/installer/ChemistryCompanion-3.0.0-Setup.exe` (~131.6 MB) |
| **Setup SHA-256** | `438912808E2ECF5FB734E0DE4E05DD8C3EECE4453F293411B0B982FD13DE1EDB` |

---

## What 3.0 ships

Chemistry Companion 3.0 is a **public research workbench**:

- Molecular analysis, heuristic IR/NMR, descriptors, exports  
- Docking workspace + PAMS protein management  
- Virtual Screening with **real** Vina docking  
- MedChem, ADMET, Lead Optimization, Research OS, Publication, Knowledge Engine  
- Optional AI via multi-provider stack  
- **First Run Experience** (no manual `.env` required)  
- Windows installer, portable onedir, and pip package  

No new product features were added during this publication packaging phase beyond FRE and distribution.

---

## Distribution channels

| Channel | Artifact | Audience |
|---------|----------|----------|
| Windows Setup | `ChemistryCompanion-3.0.0-Setup.exe` | End users (recommended) |
| Portable | `dist/ChemistryCompanion/ChemistryCompanion.exe` | Power users / offline zip |
| Python | `pip install -e .` / `pyproject.toml` 3.0.0 | Developers |

**Do not publish:** `ChemistryCompanion-1.0.0-Setup.exe`, raw `dist/` trees with QA `.env`/DB pollution, or `node_modules/`.

---

## Engineering phases completed

| Phase | Evidence | Status |
|-------|----------|--------|
| Feature complete | Workbench + research modules | ✓ |
| Workflow integrated | Project-scoped tools + docking/VS | ✓ |
| Runtime validated | Portable + installed cold start ~5 s | ✓ |
| Repository publication docs | README, CHANGELOG, CREDITS, LICENSE | ✓ |
| Dead code / mock screening | Product path mock affinities removed | ✓ |
| First Run Experience | Wizard, skip AI, OpenRouter path | ✓ |
| Portable build validated | `portable_release_validation.md` | ✓ |
| Windows installer validated | `installer_validation.md` → READY | ✓ |
| Documentation updated | This suite + packaging reports | ✓ |
| No critical issues | Residual risks non-blocking | ✓ |

---

## Version consistency (verified)

| Source | Version |
|--------|---------|
| `pyproject.toml` | 3.0.0 |
| `api/__init__.__version__` | 3.0.0 |
| `api.app` / `/health` | 3.0.0 |
| `chemistry_companion.VERSION` | 3.0.0 |
| `services.first_run_service.APP_VERSION` | 3.0.0 |
| `.env.example` `APP_VERSION` | 3.0.0 |
| `citation.cff` | 3.0.0 |
| `installer/ChemistryCompanion.iss` | 3.0.0 |
| Setup filename | `…-3.0.0-Setup.exe` |
| README badge | 3.0.0 |

---

## License & credits

| Item | Status |
|------|--------|
| `LICENSE` MIT © 2026 Aquib Belal | Present; shipped in installer as `LICENSE.txt` |
| `CREDITS.md` | Author + RDKit/Open Babel/Vina/web stack |
| `citation.cff` | 3.0.0, date-released 2026-07-13 |

---

## Documentation set for publication

| Document | Role |
|----------|------|
| `README.md` | User-facing overview and install |
| `CHANGELOG.md` | Keep a Changelog for 3.0.0 |
| `CREDITS.md` | Acknowledgments |
| `LICENSE` | MIT |
| `release_notes_v3.md` | Public release notes |
| `release_summary.md` | This executive summary |
| `release_gate.md` | Formal gate checklist |
| `installer_validation.md` | Installer acceptance |
| `portable_release_validation.md` | Portable smoke |
| `first_run_experience.md` / `fre_validation.md` | FRE design + QA |
| `final_release_audit.md` | Final quality audit |

---

## Residual risks (accepted for 3.0.0)

1. **Unsigned binaries** — SmartScreen friction  
2. **Program Files default** — prefer current-user writable install  
3. **Browser before listen** — brief first-load failure possible; refresh  
4. **Console window visible** — intentional for support  
5. **CDN UI chrome** — needs network for full styling  
6. **Heuristic spectra** — not experimental substitutes  

None of these are critical product blockers for the validated install model.

---

## Publish steps (operator)

1. Tag: `git tag -a v3.0.0 -m "Chemistry Companion 3.0.0"`  
2. Attach **only** `ChemistryCompanion-3.0.0-Setup.exe` (and optional portable zip if desired)  
3. Paste highlights from `release_notes_v3.md` into the GitHub Release body  
4. Announce install tip: current-user / LocalAppData path; leave console open  

---

## Final statement

# READY FOR PUBLIC RELEASE

**Version:** 3.0.0  
**Build:** 20260713.2254  
**Date:** 2026-07-13  
**Tag:** `v3.0.0`
