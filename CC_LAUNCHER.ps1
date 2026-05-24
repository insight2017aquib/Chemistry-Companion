# ===================================================
# Chemistry Companion Launcher (PowerShell)
# Supports Conda + Auto Installs Requirements
# ===================================================

$ProjectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectPath

$CondaEnvName = "chemistry-docking"

function Show-Menu {
    Clear-Host
    Write-Host "===================================================" -ForegroundColor Cyan
    Write-Host "              CHEMISTRY COMPANION" -ForegroundColor Cyan
    Write-Host "===================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Startup Mode" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "[1] Existing Virtual Environment (.venv)"
    Write-Host "[2] Create Virtual Environment (.venv)"
    Write-Host "[3] Use Conda Environment ($CondaEnvName)"
    Write-Host "[4] System Python"
    Write-Host "[5] Exit"
    Write-Host ""
}

function Use-CondaEnvironment {
    if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
        Write-Host "Conda not found!" -ForegroundColor Red
        return $false
    }

    Write-Host "Verifying Conda environment '$CondaEnvName'..." -ForegroundColor Green
    
    # Try running python in the environment using conda run to verify it exists and works
    & conda run -n $CondaEnvName python --version *>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Conda environment '$CondaEnvName' does not exist or is not working." -ForegroundColor Red
        Write-Host "Please create it using: conda create -n $CondaEnvName python=3.10" -ForegroundColor Yellow
        return $false
    }

    Write-Host "Conda environment '$CondaEnvName' is ready and accessible." -ForegroundColor Green
    return $true
}

function Use-ExistingVenv {
    if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
        Write-Host ".venv not found!" -ForegroundColor Red
        return $false
    }
    .\.venv\Scripts\Activate.ps1
    Write-Host "Activated existing .venv" -ForegroundColor Green
    return $true
}

function Create-Venv {
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    Write-Host "Created and activated .venv" -ForegroundColor Green
    return $true
}

function Select-Dependencies {
    $choice = Read-Host "`n[1] Dependencies already installed`n[2] Install/Update from requirements.txt`nSelect"

    if ($choice -eq "2") {
        Write-Host "`nInstalling requirements..." -ForegroundColor Yellow
        if ($global:UseConda) {
            conda run -n $CondaEnvName pip install -r requirements.txt
        } else {
            pip install -r requirements.txt
        }

        if ($LASTEXITCODE -ne 0) {
            Write-Host "Installation failed!" -ForegroundColor Red
            pause
            exit
        }
        Write-Host "Requirements installed successfully." -ForegroundColor Green
    }
}

function Start-Server {
    Write-Host "`nStarting Chemistry Companion Backend..." -ForegroundColor Cyan

    if ($global:UseConda) {
        # Use conda run for reliability
        $cmd = "cd '$ProjectPath'; conda run -n $CondaEnvName python -m uvicorn api.app:app --host 127.0.0.1 --port 8000"
    } else {
        $cmd = "cd '$ProjectPath'; python -m uvicorn api.app:app --host 127.0.0.1 --port 8000"
    }

    Start-Process powershell -ArgumentList "-NoExit", "-Command", $cmd

    Write-Host "Waiting for backend to start..." -ForegroundColor Yellow

    $attempt = 0
    while ($attempt -lt 30) {
        Start-Sleep -Seconds 2
        $attempt++
        try {
            Invoke-WebRequest -Uri "http://127.0.0.1:8000" -UseBasicParsing -TimeoutSec 2 | Out-Null
            Write-Host "`nBackend is ready!" -ForegroundColor Green
            Start-Process "http://127.0.0.1:8000"
            Write-Host "Chemistry Companion is now running." -ForegroundColor Green
            return
        } catch {
            Write-Host "." -NoNewline -ForegroundColor Yellow
        }
    }

    Write-Host "`nBackend failed to start in time." -ForegroundColor Red
}

# ====================== MAIN ======================

Show-Menu
$mode = Read-Host "Select startup mode"

$global:UseConda = $false

switch ($mode) {
    "1" {
        if (Use-ExistingVenv) {
            Select-Dependencies
            Start-Server
        }
    }
    "2" {
        if (Create-Venv) {
            Select-Dependencies
            Start-Server
        }
    }
    "3" {
        if (Use-CondaEnvironment) {
            $global:UseConda = $true
            Select-Dependencies          # ← Now also asks to install requirements in conda
            Start-Server
        }
    }
    "4" {
        Select-Dependencies
        Start-Server
    }
    "5" {
        exit
    }
    default {
        Write-Host "Invalid option." -ForegroundColor Red
    }
}