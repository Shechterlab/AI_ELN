@echo off
rem Double-click me: the same page as "Open ELN", but on a fictional practice notebook (sandbox\alex).
rem For the other one: python scripts\eln_web.py --root sandbox\jordan
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
%PY% scripts\eln_web.py --root sandbox\alex --port 8766
pause
