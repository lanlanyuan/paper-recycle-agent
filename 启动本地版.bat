@echo off
rem =====================================================================
rem  Paper Recycle Agent - local launcher
rem
rem  NOTE: this file is intentionally ASCII-only.
rem  A .bat is parsed by cmd.exe using the console code page, so UTF-8
rem  Chinese text corrupts the parse (and a UTF-8 BOM breaks line 1).
rem  Chinese docs live in README.md / docs/USAGE.md instead.
rem
rem  Usage:  double-click, or
rem          "launcher.bat"          start the web UI
rem          "launcher.bat --check"  only report the detected Python
rem =====================================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================
echo   Paper Recycle Agent - local launcher
echo ============================================
echo.

rem ---------------------------------------------------------------
rem 1. find an interpreter that can actually run Python
rem    python.exe on Windows may only be the Microsoft Store stub,
rem    which opens the Store instead of running code - so probe it.
rem ---------------------------------------------------------------
set "PYEXE="
call :probe python
if not defined PYEXE call :probe py
if not defined PYEXE call :probe python3
if not defined PYEXE goto :nopython

set "PYFULL="
set "PYVER="
for /f "delims=" %%f in ('!PYEXE! -c "import sys;sys.stdout.write(sys.version.split()[0])"') do set "PYFULL=%%f"
for /f "delims=" %%v in ('!PYEXE! -c "import sys;sys.stdout.write(str(sys.version_info[0]*100+sys.version_info[1]))"') do set "PYVER=%%v"
if not defined PYVER goto :nopython

echo [ok] interpreter: !PYEXE!   version: !PYFULL!
echo.

if /i "%~1"=="--check" goto :report

if !PYVER! LSS 307 goto :toold
if !PYVER! LSS 308 goto :coreonly
goto :web

rem ---------------------------------------------------------------
rem 2a. Python 3.8+ : install deps and start the web UI
rem ---------------------------------------------------------------
:web
echo [1/2] installing dependencies (first run needs network)...
"!PYEXE!" -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo.
  echo [warn] dependency install failed - probably no network.
  echo        Falling back to the zero-dependency offline build.
  echo.
  goto :offline
)

echo [2/2] starting server...
echo.
echo   Open in your browser:  http://localhost:8000
echo   Close this window to stop the server.
echo.
set "PYTHONPATH=src"
set "PORT=8000"
"!PYEXE!" run.py
pause
exit /b 0

rem ---------------------------------------------------------------
rem 2b. Python 3.7 : core package works, FastAPI needs 3.8+
rem ---------------------------------------------------------------
:coreonly
echo [info] Python 3.7 detected.
echo        Core statistics and the CLI work fine, but the web UI needs
echo        FastAPI, which requires Python 3.8 or newer.
echo        Opening the zero-dependency offline build instead - same
echo        features, nothing to install.
echo.
goto :offline

rem ---------------------------------------------------------------
rem 3. zero-dependency offline build
rem    Regenerated on demand so the data never goes stale.
rem ---------------------------------------------------------------
:offline
if not exist "dist\paper-recycle-offline.html" (
  echo [build] generating dist\paper-recycle-offline.html ...
  set "PYTHONPATH=src"
  "!PYEXE!" tools\build_offline.py
  if errorlevel 1 (
    echo [error] build failed. Run it manually to see the details:
    echo         set PYTHONPATH=src ^&^& "!PYEXE!" tools\build_offline.py
    pause
    exit /b 1
  )
)

if exist "dist\paper-recycle-offline.html" (
  start "" "dist\paper-recycle-offline.html"
  echo Opened: dist\paper-recycle-offline.html
) else (
  echo [error] dist\paper-recycle-offline.html not found.
)
echo.
pause
exit /b 0

rem ---------------------------------------------------------------
rem 4. no usable Python
rem ---------------------------------------------------------------
:nopython
echo [error] No usable Python found.
echo.
echo   Note: python.exe on Windows is often just a Microsoft Store stub.
echo         Double-clicking it opens the Store - it does NOT mean
echo         Python is installed.
echo.
echo   Install Python 3.7 or newer:
echo     https://www.python.org/downloads/windows/
echo   Tick "Add python.exe to PATH" during setup.
echo.
echo   No Python? The offline build needs no Python at all:
echo     dist\paper-recycle-offline.html
echo.
pause
exit /b 1

rem ---------------------------------------------------------------
rem 5. report only (diagnostics / CI)
rem ---------------------------------------------------------------
:report
echo --------------------------------------------
if !PYVER! LSS 307 goto :report_toold
if !PYVER! LSS 308 goto :report_core
echo [result] full support: web UI can start.
exit /b 0

:report_core
echo [result] core support (3.7+): CLI and offline build work; web UI needs 3.8+.
exit /b 0

:report_toold
echo [result] too old: please upgrade to Python 3.7 or newer.
exit /b 2

rem ---------------------------------------------------------------
:probe
rem probe a candidate interpreter (filters out the Store stub)
"%~1" -c "import sys" >nul 2>nul
if errorlevel 1 exit /b 0
set "PYEXE=%~1"
exit /b 0
