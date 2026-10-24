@echo off
setlocal
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "PY=py -3"
if not defined PY (
  where python >nul 2>nul && python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo Python 3.10 or newer was not found. Install it from python.org and tick "Add python.exe to PATH".
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  %PY% -m venv .venv || goto :fail
)

if not exist ".venv\.installed" (
  echo Installing dependencies from wheelhouse (offline^)...
  ".venv\Scripts\python.exe" -m pip install --no-index --find-links wheelhouse -r requirements.txt || goto :fail
  echo ok> ".venv\.installed"
)

".venv\Scripts\python.exe" -m app.main
exit /b %errorlevel%

:fail
echo.
echo Setup failed. See README.md, section "Troubleshooting".
pause
exit /b 1
