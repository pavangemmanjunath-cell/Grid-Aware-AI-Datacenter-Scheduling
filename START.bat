@echo off
rem ===========================================================================
rem  QH2DC AI Data Centre Simulator - one-click start (Windows)
rem  1. maps a short drive letter if this folder's path is long (Windows 260-char limit)
rem  2. creates a Python environment in %LOCALAPPDATA%\qh2dc\venv (short path) and installs
rem     the API requirements (again automatically whenever requirements.txt changes)
rem  3. installs the web app's npm packages on first run
rem  4. starts the FastAPI service (port 8000) and the web app (port 5173)
rem  5. opens the browser.  Stop everything with STOP.bat.
rem ===========================================================================
setlocal EnableExtensions EnableDelayedExpansion
title QH2DC launcher
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "WORK=%ROOT%"
set "VENV=%LOCALAPPDATA%\qh2dc\venv"

rem ---- short path ------------------------------------------------------------
if "!ROOT:~70,1!"=="" goto :prereq
set "DRV="
if exist "!ROOT!\.qh2dc_drive" (
  set /p DRV=<"!ROOT!\.qh2dc_drive"
  rem reuse the letter only if it still points at THIS folder
  call :mapped !DRV!
  if not defined MAPPED set "DRV="
)
if not defined DRV (
  for %%L in (Q R S T U V W X Y Z) do (
    if not defined DRV if not exist %%L:\ (
      subst %%L: "!ROOT!" >nul 2>nul && set "DRV=%%L"
    )
  )
  if not defined DRV ( echo [error] no free drive letter for SUBST & goto :fail )
  >"!ROOT!\.qh2dc_drive" echo !DRV!
)
set "WORK=!DRV!:"
echo [info] long folder path - working through drive !DRV!: ^(removed by STOP.bat^)

:prereq
rem ---- prerequisites ---------------------------------------------------------
where python >nul 2>nul || ( echo [error] Python 3.10+ not found on PATH - install it from https://www.python.org & goto :fail )
where npm >nul 2>nul || ( echo [error] Node.js 20.19+ not found on PATH - install it from https://nodejs.org & goto :fail )
call :port_free 8000 || ( echo [error] port 8000 is already in use - run STOP.bat or close the other program & goto :fail )
call :port_free 5173 || ( echo [error] port 5173 is already in use - run STOP.bat or close the other program & goto :fail )

rem ---- Python environment ----------------------------------------------------
rem The environment lives outside the repository: Python resolves drive mappings back to the long
rem real path, which breaks venv creation in deep folders.
if not exist "!VENV!\Scripts\python.exe" (
  echo [setup] creating Python environment in "!VENV!" ...
  python -m venv "!VENV!" || goto :fail
)
set "REQ=!WORK!\webapp\backend\requirements.txt"
fc /b "!REQ!" "!VENV!\qh2dc-requirements.txt" >nul 2>nul
if errorlevel 1 (
  echo [setup] installing API requirements - first run or requirements changed, a few minutes ...
  "!VENV!\Scripts\python.exe" -m pip install --upgrade pip >nul
  "!VENV!\Scripts\python.exe" -m pip install -r "!REQ!" || goto :fail
  copy /y "!REQ!" "!VENV!\qh2dc-requirements.txt" >nul
)

rem ---- web app packages ------------------------------------------------------
if not exist "!WORK!\webapp\frontend\node_modules\.bin\vite.cmd" (
  echo [setup] installing web app packages - first run only ...
  pushd "!WORK!\webapp\frontend" || goto :fail
  call npm ci || ( popd & goto :fail )
  popd
)

rem ---- start services --------------------------------------------------------
echo [start] API      http://127.0.0.1:8000/docs
set "QH2DC_DATA_DIR=!WORK!\data"
start "QH2DC API" /min cmd /c "cd /d "!WORK!\webapp\backend" && "!VENV!\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
echo [build] production build of the web app ...
pushd "!WORK!\webapp\frontend" || goto :fail
node node_modules\vite\bin\vite.js build --logLevel warn || ( popd & goto :fail )
popd
echo [start] Web app  http://127.0.0.1:5173
rem vite is started directly with node (not via npm) so that STOP.bat's tree kill reaches it
start "QH2DC Web" /min cmd /c "cd /d "!WORK!\webapp\frontend" && node node_modules\vite\bin\vite.js preview --host 127.0.0.1 --port 5173 --strictPort"

echo [wait] waiting for both services ...
for /l %%i in (1,1,90) do (
  "%SystemRoot%\System32\curl.exe" -s -o nul -m 2 http://127.0.0.1:8000/api/v1/health && "%SystemRoot%\System32\curl.exe" -s -o nul -m 2 http://127.0.0.1:5173/ && goto :ready
  ping -n 2 127.0.0.1 >nul
)
echo [error] services did not start within 90 s - see the minimised "QH2DC API" / "QH2DC Web" windows
goto :fail

:ready
echo [ok] QH2DC simulator is running. Opening the browser ...
start "" "http://127.0.0.1:5173/"
echo.
echo Close everything with STOP.bat
"%SystemRoot%\System32\timeout.exe" /t 5 >nul
exit /b 0

:port_free
netstat -ano | findstr /r /c:":%1 .*LISTENING" >nul && exit /b 1
exit /b 0

:mapped
rem sets MAPPED=1 when drive %1: is a SUBST of ROOT (findstr cannot match the backslashes reliably)
set "MAPPED="
for /f "tokens=1,* delims=>" %%a in ('subst') do (
  set "L=%%a"
  set "R=%%b"
  if /i "!L:~0,2!"=="%~1:" if /i "!R:~1!"=="!ROOT!" set "MAPPED=1"
)
exit /b 0

:fail
echo.
echo Start-up failed. Fix the message above and run START.bat again.
pause
exit /b 1
