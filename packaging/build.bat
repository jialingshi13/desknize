@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

where python >nul 2>&1
if %errorlevel%==0 (
  python "%~dp0build.py"
  goto :done
)

where py >nul 2>&1
if %errorlevel%==0 (
  py -3 "%~dp0build.py"
  goto :done
)

echo Python 3.10+ not found.
echo Install from https://www.python.org/downloads/
echo Check Add python.exe to PATH.
pause
exit /b 1

:done
if errorlevel 1 (
  pause
  exit /b 1
)
pause
exit /b 0
