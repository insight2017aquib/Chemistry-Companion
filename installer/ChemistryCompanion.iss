; ============================================================================
; Chemistry Companion — Windows Installer (Inno Setup 6)
; ============================================================================
; Builds a professional installer from the PyInstaller onedir portable build:
;   dist\ChemistryCompanion\
;
; Compile (from repository root or this folder):
;   installer\tools\InnoSetup6\ISCC.exe installer\ChemistryCompanion.iss
;
; Output:
;   dist\installer\ChemistryCompanion-3.0.0-Setup.exe
; ============================================================================

#define MyAppName "Chemistry Companion"
#define MyAppVersion "3.0.0"
#define MyAppPublisher "Aquib Belal"
#define MyAppURL "https://github.com/aquibbelal/chemistry-companion"
#define MyAppExeName "ChemistryCompanion.exe"
#define MyAppId "{{A7C3E8F1-2B4D-4E9A-9C1F-6D8E5A0B3C72}"
#define MyAppAssocName "Chemistry Companion"

; Paths relative to this .iss file
#define RepoRoot ".."
#define DistDir RepoRoot + "\dist\ChemistryCompanion"
#define AssetsDir "assets"
#define LicenseFile RepoRoot + "\LICENSE"

; Fail at *compile* time if the portable onedir build is missing
#if !FileExists(DistDir + "\" + MyAppExeName)
  #error Portable build not found — build dist\ChemistryCompanion first (chemistry_companion.spec)
#endif

[Setup]
; --- Identity / metadata ---
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppCopyright=Copyright (C) 2026 {#MyAppPublisher}
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Setup
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoTextVersion={#MyAppVersion}
VersionInfoCopyright=Copyright (C) 2026 {#MyAppPublisher}

; --- Install location ---
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=no
UsePreviousAppDir=yes
AllowNoIcons=yes

; --- Privileges: prefer Program Files; allow per-user via dialog/CLI ---
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog commandline
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; --- Wizard ---
WizardStyle=modern
WizardSizePercent=120
LicenseFile={#LicenseFile}
SetupIconFile={#AssetsDir}\chemistry_companion.ico
UninstallDisplayIcon={app}\ChemistryCompanion.ico
UninstallDisplayName={#MyAppName}
InfoBeforeFile=
InfoAfterFile=

; --- Output ---
OutputDir={#RepoRoot}\dist\installer
OutputBaseFilename=ChemistryCompanion-{#MyAppVersion}-Setup
Compression=lzma2/ultra64
SolidCompression=yes
InternalCompressLevel=ultra64
LZMAUseSeparateProcess=yes
DiskSpanning=no

; --- Upgrade / repair behaviour ---
; Same AppId => upgrade overwrites application files only.
; User data (.env, database, logs, outputs, workspaces) is NEVER in [Files],
; so upgrades preserve configuration and research artefacts.
DisableDirPage=auto
DisableReadyMemo=no
CloseApplications=yes
RestartApplications=no
AlwaysRestart=no

; --- Uninstall ---
Uninstallable=yes
CreateUninstallRegKey=yes
UninstallFilesDir={app}
UninstallLogMode=append
; EstimatedSize is also computed from [Files]; this adds empty runtime dirs (KB)
ExtraDiskSpaceRequired=10485760

; --- Misc ---
ShowLanguageDialog=no
MinVersion=10.0
UsedUserAreasWarning=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
SetupAppTitle=Setup - {#MyAppName}
SetupWindowTitle=Setup - {#MyAppName} {#MyAppVersion}
WelcomeLabel1=Welcome to the {#MyAppName} Setup Wizard
WelcomeLabel2=This will install {#MyAppName} version {#MyAppVersion} on your computer.%n%nIt is recommended that you close all other applications before continuing.
FinishedLabel=Setup has finished installing {#MyAppName} on your computer. The application may be launched by selecting the installed shortcuts.

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce
Name: "startmenu"; Description: "Create &Start Menu shortcuts"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce

[Files]
; --- Runtime application only (validated PyInstaller onedir) ---
; Installs EXE + _internal only. Does NOT ship tests, cache, archive, logs,
; temporary files, debug artifacts, development scripts, or developer DB.
Source: "{#DistDir}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#AssetsDir}\chemistry_companion.ico"; DestDir: "{app}"; DestName: "ChemistryCompanion.ico"; Flags: ignoreversion
Source: "{#DistDir}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
; Template only — never overwrites an existing user .env (different filename)
Source: "{#RepoRoot}\.env.example"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist onlyifdoesntexist
Source: "{#RepoRoot}\LICENSE"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion

[Dirs]
; Empty writable locations for first run / FRE.
; uninsneveruninstall: preserve on uninstall so research data is not destroyed.
Name: "{app}\logs"; Flags: uninsneveruninstall
Name: "{app}\outputs"; Flags: uninsneveruninstall
Name: "{app}\data"; Flags: uninsneveruninstall
Name: "{app}\data\pams"; Flags: uninsneveruninstall
Name: "{app}\outputs\docking_workspace"; Flags: uninsneveruninstall

[Icons]
; Start Menu
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\ChemistryCompanion.ico"; Comment: "Launch {#MyAppName}"; Tasks: startmenu
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"; IconFilename: "{app}\ChemistryCompanion.ico"; Comment: "Uninstall {#MyAppName}"; Tasks: startmenu
; Desktop (optional checkbox via task desktopicon)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\ChemistryCompanion.ico"; Comment: "Launch {#MyAppName}"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "Publisher"; ValueData: "{#MyAppPublisher}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "DisplayName"; ValueData: "{#MyAppName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: expandsz; ValueName: "UninstallString"; ValueData: "{uninstallexe}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "InstallSource"; ValueData: "InnoSetup-onedir"; Flags: uninsdeletekey

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent; WorkingDir: "{app}"

; User data preservation:
; - Upgrade: user .env / database / logs / outputs are not in [Files] and are preserved.
; - Uninstall: app binaries removed; user data LEFT IN PLACE (no [UninstallDelete] for those paths).
