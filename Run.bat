@echo off
setlocal EnableExtensions
cd /d "%~dp0"
where python >nul 2>&1
if %errorlevel%==0 (
  python "%~dp0run.py"
  if errorlevel 1 pause
  exit /b %errorlevel%
)
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 "%~dp0run.py"
  if errorlevel 1 pause
  exit /b %errorlevel%
)
echo Python 3.10+ not found.
pause
exit /b 1
