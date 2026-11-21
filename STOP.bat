@echo off
rem QH2DC AI Data Centre Simulator - stop the windows opened by START.bat and remove its SUBST drive.
rem Only processes in the "QH2DC API" / "QH2DC Web" windows are stopped; other programs that happen to
rem use ports 8000 or 5173 are left alone.
setlocal EnableExtensions EnableDelayedExpansion
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
for %%T in ("QH2DC API" "QH2DC Web") do (
  taskkill /FI "WINDOWTITLE eq %%~T*" /T /F >nul 2>nul && echo [stop] %%~T
)
rem belt and braces: processes started by START.bat, identified by their exact command lines
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { ($_.CommandLine -like '*vite*--host 127.0.0.1 --port 5173 --strictPort*') -or ($_.CommandLine -like '*qh2dc*venv*uvicorn app.main:app --host 127.0.0.1 --port 8000*') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
if exist "!ROOT!\.qh2dc_drive" (
  set /p DRV=<"!ROOT!\.qh2dc_drive"
  call :mapped !DRV!
  if defined MAPPED (
    subst !DRV!: /d >nul 2>nul
    echo [stop] removed drive !DRV!:
  )
  del "!ROOT!\.qh2dc_drive"
)
for %%P in (8000 5173) do (
  netstat -ano | findstr /r /c:":%%P .*LISTENING" >nul && echo [note] port %%P is still in use by another program
)
echo [ok] stopped.
"%SystemRoot%\System32\timeout.exe" /t 3 >nul
exit /b 0

:mapped
rem sets MAPPED=1 when drive %1: is a SUBST of ROOT
set "MAPPED="
for /f "tokens=1,* delims=>" %%a in ('subst') do (
  set "L=%%a"
  set "R=%%b"
  if /i "!L:~0,2!"=="%~1:" if /i "!R:~1!"=="!ROOT!" set "MAPPED=1"
)
exit /b 0
