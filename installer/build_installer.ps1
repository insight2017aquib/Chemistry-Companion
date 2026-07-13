#Requires -Version 5.1
<#
.SYNOPSIS
  Compile the Chemistry Companion Inno Setup installer.

.DESCRIPTION
  Expects a completed PyInstaller onedir build at dist\ChemistryCompanion\.
  Uses a local Inno Setup copy under installer\tools\InnoSetup6 when present.
#>
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
if (-not $Root) { $Root = (Resolve-Path "$PSScriptRoot\..").Path }
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$Iss = Join-Path $PSScriptRoot "ChemistryCompanion.iss"
$Exe = Join-Path $Root "dist\ChemistryCompanion\ChemistryCompanion.exe"
$IsccCandidates = @(
    (Join-Path $PSScriptRoot "tools\InnoSetup6\ISCC.exe"),
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "${env:LocalAppData}\Programs\Inno Setup 6\ISCC.exe"
)

if (-not (Test-Path $Exe)) {
    throw "Missing portable build: $Exe`nRun PyInstaller first (chemistry_companion.spec)."
}
if (-not (Test-Path $Iss)) {
    throw "Missing ISS script: $Iss"
}

$Iscc = $IsccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Iscc) {
    throw "ISCC.exe not found. Install Inno Setup 6 or place it under installer\tools\InnoSetup6\."
}

Write-Host "Using ISCC: $Iscc"
Write-Host "Compiling:  $Iss"
& $Iscc $Iss
if ($LASTEXITCODE -ne 0) {
    throw "ISCC failed with exit code $LASTEXITCODE"
}

$Out = Join-Path $Root "dist\installer\ChemistryCompanion-3.0.0-Setup.exe"
if (-not (Test-Path $Out)) {
    throw "Expected output missing: $Out"
}
$info = Get-Item $Out
Write-Host ("Installer ready: {0} ({1:N1} MB)" -f $info.FullName, ($info.Length / 1MB))
