#!/usr/bin/env bash
# Run the web interface (macOS / Linux).
# Creates a virtual environment and installs dependencies on first launch.
set -e
cd "$(dirname "$0")"

# Pick a Python 3 interpreter (override with PYTHON=/path/to/python).
PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  for cand in python3.12 python3.11 python3.10 python3; do
    if command -v "$cand" >/dev/null 2>&1; then PY="$cand"; break; fi
  done
fi
if [ -z "$PY" ]; then
  echo "❌ Python 3 not found. Install Python 3.10+ and retry." >&2
  exit 1
fi

if [ ! -d .venv ]; then
  echo "Creating virtual environment ($("$PY" --version 2>&1))..."
  "$PY" -m venv .venv
  .venv/bin/pip install --upgrade pip -q
  .venv/bin/pip install -r requirements.txt
fi

exec .venv/bin/python app.py
