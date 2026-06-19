@echo off
REM Run the web interface (Windows).
REM Creates a virtual environment and installs dependencies on first launch.
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python 3 not found. Install Python 3.10+ from https://www.python.org and retry.
  exit /b 1
)

if not exist ".venv" (
  echo Creating virtual environment...
  python -m venv .venv
  .venv\Scripts\python.exe -m pip install --upgrade pip -q
  .venv\Scripts\pip.exe install -r requirements.txt
)

.venv\Scripts\python.exe app.py
endlocal
