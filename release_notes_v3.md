# Chemistry Companion 3.0.0 — Release Notes

| Field | Value |
|-------|-------|
| **Version** | 3.0.0 |
| **Build** | 20260713.2254 |
| **Release date** | 2026-07-13 |
| **Git tag** | `v3.0.0` |
| **License** | MIT |
| **Author** | Aquib Belal |
| **Primary artifact** | `ChemistryCompanion-3.0.0-Setup.exe` |

---

## Highlights

Chemistry Companion **3.0** is a full research workbench release: molecular analysis and heuristic spectra, docking workspace, protein assets, virtual screening, and medicinal-chemistry research modules — available as a **Windows installer** (no Python required), a **portable EXE**, or a **pip-installable** Python package.

First launch includes a **First Run Experience** so users can configure paths and optional AI (or skip AI) without manually creating a `.env` file.

---

## What's new in 3.0

### Research workbench

- Dashboard, single-molecule analysis, batch, spectra, history, settings
- **Docking workspace** — protein prep, grid, AutoDock Vina, pose analysis
- **PAMS** — fetch/upload/manage protein structures
- **Virtual Screening** — library docking with **real** ligand preparation and Vina
- **MedChem, ADMET, Lead Optimization, Research OS, Publication Assistant, Knowledge Engine**
- Optional multi-provider AI explanations with graceful fallback without API keys

### First Run Experience

- Auto-redirect to Setup Wizard on first launch
- Configure AI (OpenRouter, OpenAI, Groq, Ollama) or **Skip / disable AI**
- Test connection with friendly error messages (no stack traces in UI)
- Writes `.env` and completion marker; wizard does not reappear after successful setup
- Re-open anytime from **Settings → Setup Wizard**

### Packaging & distribution

- Production `pyproject.toml` (`chemistry-companion==3.0.0`)
- Console entry points: `chemistry-companion`, `chemistry-companion-server`
- PyInstaller **onedir** portable build
- Windows **Inno Setup** installer: license, icon, desktop/Start Menu shortcuts, uninstaller
- Upgrade preserves database, workspace, and configuration
- Uninstall removes program files; **user research data is kept** by design

---

## Download / install

### Windows (recommended for most users)

1. Download **`ChemistryCompanion-3.0.0-Setup.exe`**
2. Run Setup and accept the MIT license
3. Prefer **install for current user** or a **writable** folder  
   (recommended: `%LOCALAPPDATA%\Programs\Chemistry Companion`)
4. Launch **Chemistry Companion** from the desktop or Start Menu
5. Complete or skip the Setup Wizard
6. Application opens at `http://127.0.0.1:8000`

**First launch tips**

- A console window is expected; leave it open while you work.
- First start may take ~5–15 seconds; if the browser shows an error, wait and refresh.
- Windows SmartScreen may warn because the Setup is not code-signed — use *More info → Run anyway* if you trust the source.

### Portable

Use the `ChemistryCompanion` onedir folder and run `ChemistryCompanion.exe`.

### Developers

```bash
pip install -e ".[dev]"
chemistry-companion-server
```

Optional: use **Settings → Setup Wizard**, or copy `.env.example` → `.env` for LLM keys.

---

## Requirements

| Audience | Need |
|----------|------|
| Windows installer / portable | Windows 10+ x64; **no** system Python |
| Online UI | Internet for CDN assets (Tailwind, HTMX, Plotly, 3Dmol, …) |
| Full docking / screening | Bundled Vina + Open Babel (included in portable/installer) |
| IUPAC name resolution | System **JRE** (OPSIN) when using name input |
| AI features | API keys via Setup Wizard or `.env` (optional) |

---

## Breaking / version notes

- Public product version is **3.0.0** (earlier packaging experiments used 1.0.0 labels).
- Windows Setup AppId is stable; reinstalling upgrades in place and preserves user data.

---

## Known limitations

1. Spectral predictions are **heuristic**, not DFT or experimental replacements.  
2. UI styling depends on **CDN** assets (use online).  
3. JSON `POST /api/analyze` has a known serialization issue; the **web analysis form** works.  
4. Setup/EXE are **not code-signed**; SmartScreen may warn.  
5. Default Program Files install may block writes for standard users — use a current-user install path.  
6. Console window remains visible (by design for troubleshooting in 3.0.0).

---

## Validation summary

| Area | Status |
|------|--------|
| Feature complete workbench | Validated |
| Research workflows integrated | Validated |
| Runtime / portable smoke | Validated (`portable_release_validation.md`) |
| First Run Experience | Validated (`fre_validation.md`) |
| Windows installer acceptance | Validated (`installer_validation.md`) — **READY** |
| Final startup audit | Conditional GO with install guidance (`final_release_audit.md`) |

Full history: [`CHANGELOG.md`](CHANGELOG.md).

---

## Credits & citation

- Credits: [`CREDITS.md`](CREDITS.md)  
- License: [`LICENSE`](LICENSE)  
- Citation: [`citation.cff`](citation.cff) (version 3.0.0)

---

## Support

Project repository: https://github.com/aquibbelal/chemistry-companion  

When reporting issues, include: OS version, install type (Setup / portable / pip), and `logs/chemistry_companion.log` when available.
