# Chemistry Companion — Windows Installer Report

**Date:** 2026-07-13  
**Installer technology:** Inno Setup 6.4.3  
**Setup package:** `dist/installer/ChemistryCompanion-1.0.0-Setup.exe`  
**Setup size:** ~131.6 MB (compressed; expands to ~400 MB on disk)  
**Source payload:** PyInstaller onedir `dist/ChemistryCompanion/`  
**Application version:** 1.0.0  
**Publisher:** Aquib Belal  

---

## 1. Executive summary

A professional Windows installer was produced with Inno Setup and fully verified:

| Capability | Status |
|------------|--------|
| Desktop shortcut | Pass |
| Start Menu shortcuts (app + uninstall) | Pass |
| Uninstaller + Add/Remove Programs | Pass |
| Application icon | Pass (`ChemistryCompanion.ico`) |
| License page (MIT) | Pass |
| Version / publisher metadata | Pass |
| Installation directory | Pass (`{autopf}\Chemistry Companion` default) |
| Clean install | Pass |
| Upgrade (re-run Setup, same AppId) | Pass |
| Repair (re-run Setup) | Pass |
| Uninstall | Pass |
| Application launch (Dashboard HTTP 200) | Pass |

**No application source changes** were required for installation (installer-only assets + ISS).

---

## 2. Installer configuration

### 2.1 Script and assets

| Path | Role |
|------|------|
| `installer/ChemistryCompanion.iss` | Inno Setup script |
| `installer/build_installer.ps1` | Compile helper |
| `installer/assets/chemistry_companion.ico` | Multi-size app/setup icon |
| `installer/assets/make_icon.py` | Icon generator (Pillow) |
| `installer/tools/InnoSetup6/` | Local Inno Setup compiler (optional bootstrap) |
| `LICENSE` | License agreement shown in wizard |
| `dist/ChemistryCompanion/` | Packaged application (must exist before compile) |

### 2.2 Identity & version metadata

| Field | Value |
|-------|-------|
| AppId (upgrade identity) | `{A7C3E8F1-2B4D-4E9A-9C1F-6D8E5A0B3C72}` |
| AppName | Chemistry Companion |
| AppVersion | 1.0.0 |
| AppPublisher | Aquib Belal |
| AppPublisherURL / Support / Updates | https://github.com/aquibbelal/chemistry-companion |
| AppCopyright | Copyright (C) 2026 Aquib Belal |
| VersionInfoVersion | 1.0.0.0 |
| VersionInfoProductName | Chemistry Companion |
| OutputBaseFilename | `ChemistryCompanion-1.0.0-Setup` |

### 2.3 Wizard options

| Setting | Value |
|---------|-------|
| WizardStyle | modern |
| LicenseFile | repository `LICENSE` (MIT) |
| SetupIconFile | `installer/assets/chemistry_companion.ico` |
| UninstallDisplayIcon | `{app}\ChemistryCompanion.ico` |
| Compression | `lzma2/ultra64`, solid |
| Architectures | x64compatible, 64-bit install mode |
| MinVersion | Windows 10 |
| PrivilegesRequired | `admin` (default Program Files) |
| PrivilegesRequiredOverridesAllowed | `dialog commandline` (supports `/CURRENTUSER`) |
| DefaultDirName | `{autopf}\Chemistry Companion` |
| DefaultGroupName | Chemistry Companion |
| CloseApplications | yes (helps upgrade/repair) |

### 2.4 Files installed

| Source | Destination |
|--------|-------------|
| `ChemistryCompanion.exe` | `{app}\` |
| `_internal\**` | `{app}\_internal\` (full onedir payload) |
| `chemistry_companion.ico` | `{app}\ChemistryCompanion.ico` |
| `.env.example` | `{app}\` |
| `LICENSE` | `{app}\LICENSE.txt` |

Empty runtime directories created at install:

- `{app}\logs`
- `{app}\outputs`
- `{app}\data`
- `{app}\data\pams`
- `{app}\outputs\docking_workspace`

Build-machine SQLite DB / validation outputs are **not** packaged (only EXE + `_internal`).

### 2.5 Tasks

| Task | Description | Default |
|------|-------------|---------|
| `desktopicon` | Create desktop shortcut | checked once |
| `startmenu` | Create Start Menu shortcuts | checked once |

### 2.6 Build commands

```powershell
# 1) Portable onedir (if not already built)
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean chemistry_companion.spec

# 2) Compile installer
.\installer\tools\InnoSetup6\ISCC.exe .\installer\ChemistryCompanion.iss
# or
powershell -File .\installer\build_installer.ps1
```

Output: `dist\installer\ChemistryCompanion-1.0.0-Setup.exe`

### 2.7 Silent install examples

```powershell
# All-users (requires elevation) — default Program Files
.\ChemistryCompanion-1.0.0-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART

# Per-user
.\ChemistryCompanion-1.0.0-Setup.exe /VERYSILENT /CURRENTUSER /DIR="%LOCALAPPDATA%\Programs\Chemistry Companion"

# Custom tasks
.\ChemistryCompanion-1.0.0-Setup.exe /VERYSILENT /TASKS=desktopicon,startmenu
```

---

## 3. Registry entries

### 3.1 Application keys (`HKA` = HKLM or HKCU depending on install mode)

Under:

```text
Software\Aquib Belal\Chemistry Companion
```

| Value name | Type | Data |
|------------|------|------|
| InstallPath | string | `{app}` |
| Version | string | `1.0.0` |
| Publisher | string | `Aquib Belal` |
| DisplayName | string | `Chemistry Companion` |
| UninstallString | expandsz | `{uninstallexe}` |

Flags: `uninsdeletekey` — entire key removed on uninstall.

### 3.2 Windows Add/Remove Programs (automatic)

Inno Setup creates a standard uninstall key under:

```text
HKLM or HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\{AppId}_is1
```

Typical values (managed by Inno):

| Value | Purpose |
|-------|---------|
| DisplayName | Chemistry Companion |
| DisplayVersion | 1.0.0 |
| Publisher | Aquib Belal |
| InstallLocation | Install directory |
| UninstallString | Path to `unins000.exe` |
| DisplayIcon | `{app}\ChemistryCompanion.ico` |
| EstimatedSize | Approx. installed size |

### 3.3 Verification snapshot (per-user install)

```text
HKCU\Software\Aquib Belal\Chemistry Companion
  InstallPath = …\AppData\Local\Programs\Chemistry Companion Verify
  Version     = 1.0.0

UninstallString = …\unins000.exe
```

After uninstall: app registry key and ARP entry **removed**.

---

## 4. Shortcuts

### 4.1 Desktop

| Property | Value |
|----------|-------|
| Name | `Chemistry Companion.lnk` |
| Target | `{app}\ChemistryCompanion.exe` |
| Working directory | `{app}` |
| Icon | `{app}\ChemistryCompanion.ico` |
| Task | `desktopicon` |
| Location | `{autodesktop}` (public or user desktop) |

### 4.2 Start Menu

Group: `{group}` → **Chemistry Companion**

| Shortcut | Target |
|----------|--------|
| Chemistry Companion | `{app}\ChemistryCompanion.exe` |
| Uninstall Chemistry Companion | `{uninstallexe}` |

Icons use `ChemistryCompanion.ico`. Created when task `startmenu` is selected.

### 4.3 Verification

| Check | Result |
|-------|--------|
| Desktop `.lnk` after install | Present |
| Start Menu app `.lnk` | Present |
| Start Menu uninstall `.lnk` | Present |
| Desktop + Start Menu removed after uninstall | Pass |

---

## 5. Uninstall procedure

### 5.1 End-user methods

1. **Settings → Apps → Installed apps** → Chemistry Companion → Uninstall  
2. **Start Menu** → Chemistry Companion → Uninstall Chemistry Companion  
3. Run `{app}\unins000.exe`  
4. Silent:

```powershell
& "{app}\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
```

### 5.2 What uninstall removes

| Item | Removed? |
|------|----------|
| `{app}\ChemistryCompanion.exe` | Yes |
| `{app}\_internal\**` | Yes |
| Shortcuts (desktop + Start Menu) | Yes |
| App registry key + ARP entry | Yes |
| Uninstaller itself | Yes |
| `{app}\logs`, `outputs`, `data` | Yes (`[UninstallDelete]`) |
| `{app}\chemistry_companion.db` | Yes |
| `{app}\.env` (if user created) | Yes |
| `{app}\ChemistryCompanion.ico` | Yes |

### 5.3 Verified uninstall result

- EXE gone  
- Desktop and Start Menu shortcuts gone  
- `HKCU\Software\Aquib Belal\Chemistry Companion` gone  
- ARP uninstall entry gone  
- Uninstaller exit code **0**

---

## 6. Verification matrix

Automated silent lifecycle (`/CURRENTUSER`, custom DIR under `%LOCALAPPDATA%\Programs\…`):

| Step | Result |
|------|--------|
| 1. Clean install | Exit 0; EXE, `_internal`, icon, license, dirs present |
| 2. Desktop / Start Menu shortcuts | Present |
| 3. Registry + ARP | Present; Version=1.0.0 |
| 4. Launch app | Dashboard `HTTP 200` in ~8 s (port 8766 test) |
| 5. Upgrade (re-run Setup) | Exit 0; files + shortcuts intact |
| 6. Repair (re-run Setup) | Exit 0; templates/static present |
| 7. Uninstall | Exit 0; files, shortcuts, registry, ARP removed |

Logs written under `dist/installer/verify_logs/` during QA.

---

## 7. Known limitations

| Limitation | Detail | Mitigation |
|------------|--------|------------|
| **Large install footprint** | ~400 MB on disk after install | Expected (RDKit/SciPy/Open Babel); slim PyInstaller bundle later |
| **Large Setup EXE** | ~132 MB download | LZMA2 already applied; delta updates not implemented |
| **Admin default** | Default install targets Program Files | Wizard / `/CURRENTUSER` allow per-user install |
| **Unsigned binary** | No Authenticode signature | SmartScreen may warn; code-sign for production release |
| **EXE icon in taskbar** | PyInstaller EXE may still show default console icon | Shortcuts use custom `.ico`; re-link PyInstaller with icon for EXE resource if desired |
| **CDN UI assets** | Tailwind/HTMX/Plotly/3Dmol need network | Documented offline risk from portable build |
| **No separate “Repair” ARP button** | Windows repair = re-run Setup with same AppId | Documented; works as verified |
| **User data deleted on uninstall** | DB/logs/outputs removed via `[UninstallDelete]` | Acceptable for clean uninstall; change if data retention is required |
| **JRE not installed** | OPSIN IUPAC conversion needs system Java | Optional prerequisite documentation |
| **Console window** | App is console-mode for diagnostics | Future windowed/bootloader change if desired |
| **Single language** | English wizard only | Additional `[Languages]` entries can be added |

---

## 8. Upgrade policy

- **Same AppId** across releases ensures Setup detects prior installs and upgrades in place.  
- `UsePreviousAppDir=yes` reuses the previous install directory.  
- `Flags: ignoreversion` on files forces overwrite of application binaries on upgrade/repair.  
- Bump `#define MyAppVersion` and `VersionInfoVersion` for each release; keep **AppId constant**.

---

## 9. Distribution checklist

```text
[x] Inno Setup script with license, icon, shortcuts, uninstaller
[x] Publisher + version metadata in Setup EXE
[x] Registry install path / version
[x] Desktop + Start Menu shortcuts
[x] Clean install verified
[x] Upgrade verified
[r] Repair verified (reinstall)
[x] Uninstall verified
[x] Application launch verified
[ ] Code signing (recommended before public release)
[ ] VirusTotal / SmartScreen reputation (post-signing)
```

---

## 10. Conclusion

Chemistry Companion ships a professional Windows installer:

**`dist/installer/ChemistryCompanion-1.0.0-Setup.exe`**

It installs the validated PyInstaller onedir build, presents the MIT license, records publisher/version metadata, creates desktop and Start Menu shortcuts, registers uninstall information, and cleanly removes the product. Install, upgrade, repair, uninstall, and application launch were verified successfully.
