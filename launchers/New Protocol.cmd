@echo off
rem Double-click me.
setlocal
cd /d "%~dp0\.."
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY (
  echo Python 3 is needed. Install it from https://www.python.org/downloads/
  echo ^(tick "Add python.exe to PATH" during install^), then double-click me again.
  pause
  exit /b 1
)
%PY% scripts\eln.py new protocol --interactive --open
echo.
echo Done.
pause
