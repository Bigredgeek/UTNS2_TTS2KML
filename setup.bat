@echo off
setlocal EnableDelayedExpansion

REM ============================================================
REM  UTNS2 TTS -> KML  :  one-time environment setup
REM  Installs Python (if missing) and the Python packages this
REM  project needs (pykml, lxml, numpy, lupa).
REM  Safe to re-run; it skips anything already present.
REM ============================================================

echo.
echo === UTNS2 TTS2KML setup =====================================
echo This will make sure Python and the required packages are installed.
echo.

REM --- Move to the folder this script lives in ---
cd /d "%~dp0"

REM ------------------------------------------------------------
REM 1) Find a working Python
REM ------------------------------------------------------------
set "PY="
REM Prefer the Windows 'py' launcher, then plain 'python'.
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY (
    python --version >nul 2>&1 && set "PY=python"
)

if defined PY (
    echo [OK] Found Python: 
    %PY% --version
    goto :have_python
)

REM ------------------------------------------------------------
REM 2) No Python -> try to install it with winget
REM ------------------------------------------------------------
echo [..] Python was not found. Attempting to install it...
where winget >nul 2>&1
if errorlevel 1 (
    echo.
    echo [X] 'winget' is not available on this PC, so Python can't be
    echo     installed automatically.
    echo.
    echo     Please install Python 3 manually from:
    echo         https://www.python.org/downloads/windows/
    echo     IMPORTANT: tick "Add python.exe to PATH" in the installer.
    echo     Then re-run this setup.bat.
    echo.
    pause
    exit /b 1
)

echo [..] Installing Python 3.12 via winget (you may see a UAC prompt)...
winget install --id Python.Python.3.12 -e --source winget ^
    --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
    echo.
    echo [X] winget could not install Python automatically.
    echo     Install it manually from https://www.python.org/downloads/windows/
    echo     (tick "Add python.exe to PATH"), then re-run setup.bat.
    echo.
    pause
    exit /b 1
)

REM PATH usually isn't refreshed inside this same window, so re-detect.
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY (
    python --version >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo.
    echo [!] Python was installed, but this window doesn't see it yet.
    echo     Close this window, open a NEW one, and run setup.bat again
    echo     to finish installing the packages.
    echo.
    pause
    exit /b 0
)

:have_python
echo.

REM ------------------------------------------------------------
REM 3) Upgrade pip, then install the project requirements
REM ------------------------------------------------------------
echo [..] Upgrading pip...
%PY% -m pip install --upgrade pip
if errorlevel 1 (
    echo [X] Failed to upgrade pip. Check your internet connection.
    pause
    exit /b 1
)

echo.
if exist "requirements.txt" (
    echo [..] Installing required packages from requirements.txt...
    %PY% -m pip install -r requirements.txt
) else (
    echo [..] requirements.txt not found; installing packages directly...
    %PY% -m pip install pykml lxml numpy lupa
)
if errorlevel 1 (
    echo.
    echo [X] Package installation failed. See the messages above.
    pause
    exit /b 1
)

echo.
echo === Setup complete! ========================================
echo You can now run process_maps.bat to convert a TTS save to KML.
echo.
pause
exit /b 0
