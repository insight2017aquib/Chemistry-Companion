# Installer Structure — Chemistry Companion 3.0.0

**Setup:** `dist/installer/ChemistryCompanion-3.0.0-Setup.exe`  
**Technology:** Inno Setup 6  
**Payload:** PyInstaller onedir (`ChemistryCompanion.exe` + `_internal`)  

---

## 1. Default installation directory

| Mode | Path |
|------|------|
| All-users (default) | `{autopf}\Chemistry Companion` → e.g. `C:\Program Files\Chemistry Companion` |
| Per-user (`/CURRENTUSER`) | User-chosen; QA used `%LOCALAPPDATA%\Programs\…` |

Working directory for the app: `{app}` (install root).

---

## 2. Installed directory layout

```text
{app}/
├── ChemistryCompanion.exe          # Portable entry (Uvicorn + FRE)
├── ChemistryCompanion.ico          # Shortcuts / ARP icon
├── LICENSE.txt                     # MIT
├── .env.example                    # Template only (if not already present)
├── unins000.exe                    # Uninstaller
├── unins000.dat
│
├── logs/                           # Empty at install; runtime logs (preserved)
├── outputs/                        # Exports / docking (preserved)
│   └── docking_workspace/
├── data/                           # Runtime data (preserved)
│   └── pams/                       # Protein assets
│
└── _internal/                      # PyInstaller payload (sys._MEIPASS)
    ├── templates/                  # Includes setup_wizard.html
    ├── static/css|js|...
    ├── data/*.csv                  # Sample benchmarks
    ├── openbabel/bin/...
    ├── vina.exe
    ├── obabel.exe
    ├── rdkit.libs/ ...
    └── … Python runtime + site-packages …

After first FRE completion (created at runtime, not by Setup):
├── .env
├── .cc_setup_complete
└── chemistry_companion.db
```

### Explicitly **not** installed

- `tests/`, `archive/`, `scripts/`, `docs/`  
- Build-machine `logs/`, `outputs/` contents, screenshots  
- Developer `.env` / SQLite from the CI machine  
- Cleanup reports, cache, temporary debug files  

---

## 3. Installed files (categories)

| Category | Contents |
|----------|----------|
| Application | `ChemistryCompanion.exe` |
| Runtime payload | Entire `_internal\` tree from validated onedir |
| Branding | `ChemistryCompanion.ico` |
| Legal | `LICENSE.txt` |
| Config template | `.env.example` |
| Uninstaller | `unins000.exe` / `.dat` |
| Empty runtime dirs | `logs`, `outputs`, `data`, `data\pams`, `outputs\docking_workspace` |

---

## 4. Shortcuts

| Shortcut | Target | Task |
|----------|--------|------|
| Start Menu → Chemistry Companion → Chemistry Companion | `{app}\ChemistryCompanion.exe` | `startmenu` |
| Start Menu → Chemistry Companion → Uninstall Chemistry Companion | `{uninstallexe}` | `startmenu` |
| Desktop → Chemistry Companion | `{app}\ChemistryCompanion.exe` | `desktopicon` (optional checkbox) |

Icon file: `{app}\ChemistryCompanion.ico`  
Working directory: `{app}`  

---

## 5. Registry entries

Root: **HKA** (`HKLM` for all-users, `HKCU` for per-user)

```text
Software\Aquib Belal\Chemistry Companion
  InstallPath      = {app}
  Version          = 3.0.0
  Publisher        = Aquib Belal
  DisplayName      = Chemistry Companion
  UninstallString  = {uninstallexe}
  InstallSource    = InnoSetup-onedir
```

Flags: `uninsdeletekey` (app key removed on uninstall).

### Add/Remove Programs (automatic Inno)

```text
…\Uninstall\{A7C3E8F1-2B4D-4E9A-9C1F-6D8E5A0B3C72}_is1
  DisplayName, DisplayVersion, Publisher, InstallLocation,
  UninstallString, DisplayIcon, EstimatedSize, …
```

AppId (upgrade identity):

```text
{A7C3E8F1-2B4D-4E9A-9C1F-6D8E5A0B3C72}
```

---

## 6. Upgrade behaviour

| Action | Result |
|--------|--------|
| Re-run Setup same AppId | In-place upgrade / repair |
| Application binaries | Replaced |
| `.env` | **Kept** |
| Database | **Kept** |
| `logs/`, `outputs/`, `data/` | **Kept** |
| Previous install dir | Reused (`UsePreviousAppDir=yes`) |

Do **not** change AppId unless intentionally breaking upgrade chain.

---

## 7. Uninstall behaviour

| Removed | Preserved (by design) |
|---------|------------------------|
| `ChemistryCompanion.exe` | `.env` |
| `_internal\` | `chemistry_companion.db` |
| Shortcuts | `logs\`, `outputs\`, `data\` |
| App registry key + ARP entry | User research artefacts |
| Uninstaller itself | |

Users may manually delete the install folder to remove residual user data.

---

## 8. First Run Experience after install

```text
Install Setup
    → Launch ChemistryCompanion.exe
        → No .env / no setup complete
            → Middleware: GET /  →  307 /setup
            → Setup Wizard (Begin Setup / Skip)
            → Writes .env + .cc_setup_complete
            → Subsequent launches: Dashboard (no wizard)
```

Verified after silent install of `ChemistryCompanion-3.0.0-Setup.exe`.

---

## 9. Size guidance

| Metric | Approx. |
|--------|---------|
| Setup EXE (compressed) | ~132 MB |
| On-disk after install | ~400 MB |
| Extra reserved for empty runtime dirs | 10 MB (`ExtraDiskSpaceRequired`) |

---

## 10. Related documents

| Document | Purpose |
|----------|---------|
| `installer_build_report.md` | Build + QA evidence |
| `installer/ChemistryCompanion.iss` | Source of truth for structure |
| `portable_release_validation.md` | Onedir validation before this installer |
| `docs/changelog/win_setup_file.md` | Packaging engineering handover |

---

## 11. Known limitations

- Not code-signed.  
- Large scientific runtime footprint.  
- Uninstall does not wipe user data (intentional).  
- CDN UI assets still require network after install.  
