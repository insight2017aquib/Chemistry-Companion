@echo off
title Chemistry Companion Launcher
color 0A

cd /d "%~dp0"

:MENU

cls
echo ===================================================
echo              CHEMISTRY COMPANION
echo ===================================================
echo.
echo Startup Mode
echo.
echo [1] Existing Virtual Environment
echo [2] Create Virtual Environment
echo [3] System Python
echo [4] Exit
echo.

set /p MODE=Select startup mode:

if "%MODE%"=="1" goto USEVENV
if "%MODE%"=="2" goto CREATEVENV
if "%MODE%"=="3" goto SYSTEMPY
if "%MODE%"=="4" exit

goto MENU


:CHECKPYTHON

where python >nul 2>&1

if errorlevel 1 (

echo Python missing.
pause
exit

)

goto :eof


:USEVENV

call :CHECKPYTHON

if not exist ".venv\Scripts\activate.bat" (

echo Virtual environment missing.
pause
goto MENU

)

call ".venv\Scripts\activate.bat"

goto DEPSELECT


:CREATEVENV

call :CHECKPYTHON

echo Creating venv...

python -m venv .venv

call ".venv\Scripts\activate.bat"

goto INSTALLREQ


:SYSTEMPY

call :CHECKPYTHON

goto DEPSELECT


:DEPSELECT

cls

echo Dependencies
echo.
echo [1] Already Installed
echo [2] Install Requirements
echo.

set /p DEP=Select:

if "%DEP%"=="1" goto STARTSERVER
if "%DEP%"=="2" goto INSTALLREQ

goto DEPSELECT


:INSTALLREQ

echo Installing requirements...

pip install -r requirements.txt

if errorlevel 1 (

echo Installation failed.
pause
exit

)

goto STARTSERVER


:STARTSERVER

cls

echo ==========================================
echo Starting Chemistry Companion Backend
echo ==========================================
echo.

start "ChemistryBackend" cmd /c ^
python -m uvicorn api.app:app --host 127.0.0.1 --port 8000

echo.
echo Waiting for backend...

:WAITLOOP

powershell -Command ^
"try {Invoke-WebRequest http://127.0.0.1:8000 -UseBasicParsing -TimeoutSec 2 > $null; exit 0} catch {exit 1}"

if errorlevel 1 (

timeout /t 2 >nul

goto WAITLOOP

)

echo.
echo Backend detected.

echo Opening Chemistry Companion...

start "" http://127.0.0.1:8000

echo.
echo Chemistry Companion ready.

exit