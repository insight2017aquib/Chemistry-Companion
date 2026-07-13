# Installer Build Report — Chemistry Companion 3.0.0

**Date:** 2026-07-13  
**Role:** Senior Windows Release Engineer  
**Source payload:** Validated PyInstaller onedir only (`dist/ChemistryCompanion/`)  
**PyInstaller rebuild:** **Not performed** (per mission)  
**Tool:** Inno Setup 6.4.3 (`installer/tools/InnoSetup6/ISCC.exe`)  
**Script:** `installer/ChemistryCompanion.iss`  

---

## Outcome

| Item | Result |
|------|--------|
| Setup package | **`dist/installer/ChemistryCompanion-3.0.0-Setup.exe`** |
| Compile | **SUCCESS** (exit 0, ~256 s) |
| Setup size | **~131.6 MB** (138,005,950 bytes) |
| Silent install QA | **PASS** (exit 0) |
| FRE on first launch | **PASS** (`GET /` → 307 `/setup`) |
| Upgrade preserves user data | **PASS** (marker, `.env`, DB retained) |
| Desktop + Start Menu shortcuts | **PASS** |
| Registry metadata | **PASS** |

---

## Build process

```text
Input:  dist/ChemistryCompanion/ChemistryCompanion.exe
        dist/ChemistryCompanion/_internal/**  (validated FRE portable)
Script: installer/ChemistryCompanion.iss
Output: dist/installer/ChemistryCompanion-3.0.0-Setup.exe
```

Command used:

```powershell
.\installer\tools\InnoSetup6\ISCC.exe .\installer\ChemistryCompanion.iss
```

**Not used:** source rebuild, `pip install`, PyInstaller re-run.

---

## Installer features implemented

| Requirement | Implementation |
|-------------|----------------|
| Professional wizard | `WizardStyle=modern`, license page, welcome/finished messages |
| Application icon | `installer/assets/chemistry_companion.ico` → `{app}\ChemistryCompanion.ico` |
| Version information | 3.0.0 / VersionInfo 3.0.0.0 |
| Publisher | Aquib Belal |
| Product name | Chemistry Companion |
| Desktop shortcut | Task `desktopicon` (optional checkbox, checked once by default) |
| Start Menu shortcut | Task `startmenu` (app + Uninstall) |
| Uninstaller | `unins000.exe` + ARP entry |
| Estimated size | Computed from `[Files]` + `ExtraDiskSpaceRequired=10MB` for empty runtime dirs |
| Default directory | `{autopf}\Chemistry Companion` → typically `C:\Program Files\Chemistry Companion` |

---

## Install only runtime files

| Installed | Not installed |
|-----------|----------------|
| `ChemistryCompanion.exe` | `tests/` |
| `_internal/**` (runtime code, templates, static, natives) | `archive/`, screenshots |
| `ChemistryCompanion.ico` | Developer `logs/` from build machine |
| `LICENSE.txt` | Temporary / debug artifacts |
| `.env.example` (only if missing) | `.env` from build machine |
| Empty `logs/`, `outputs/`, `data/` dirs | Cleanup reports, development scripts |

User research data is **never** packaged from the build tree.

---

## Upgrade strategy

| Asset | Upgrade behaviour |
|-------|-------------------|
| Application EXE + `_internal` | Overwritten (`ignoreversion`) |
| `.env` | **Preserved** (not in `[Files]`) |
| `chemistry_companion.db` | **Preserved** |
| `logs/`, `outputs/`, `data/` | **Preserved** (`uninsneveruninstall` on dirs) |
| Workspaces under `outputs/` | **Preserved** |

AppId (stable): `{A7C3E8F1-2B4D-4E9A-9C1F-6D8E5A0B3C72}`

QA: after install + FRE skip, marker file and appended `.env` content survived a second silent Setup run. (Upgrade process exit code **5** observed once — typically app-in-use/close warning; data still preserved.)

---

## First Run Experience verification (post-install)

| Check | Result |
|-------|--------|
| Fresh install has no `.env` | **True** |
| First launch (frozen) | **PASS** |
| `GET /` → **307** `/setup` | **PASS** |
| Wizard shows “Begin Setup” | **PASS** |
| Skip completes → Dashboard 200 | **PASS** |

FRE runs **only** when setup incomplete (no marker / no `CHEM_COMPANION_SETUP_COMPLETE`).

---

## Silent install example

```powershell
# All-users (elevation)
.\ChemistryCompanion-3.0.0-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART

# Per-user
.\ChemistryCompanion-3.0.0-Setup.exe /VERYSILENT /CURRENTUSER ^
  /DIR="%LOCALAPPDATA%\Programs\Chemistry Companion" ^
  /TASKS=desktopicon,startmenu
```

---

## Known limitations

1. Setup/EXE **not Authenticode-signed** (SmartScreen may warn).  
2. Default install under Program Files needs admin; `/CURRENTUSER` supported.  
3. Uninstall leaves user data in place by design (manual folder delete for full wipe).  
4. Upgrade exit code 5 can appear if the app is still running; close app before upgrade for exit 0.  
5. Installer size ~132 MB compressed; ~400 MB on disk after install.

---

## Summary

Production Inno Setup installer built **from the validated portable onedir**, verified install layout, shortcuts, registry, FRE first-launch behaviour, and upgrade data preservation. No scientific workflow changes.
