#!/usr/bin/env sh
# Start LexiHover on macOS / Linux. Creates .venv and installs from wheelhouse/ (offline) on first run.
set -e
cd "$(dirname "$0")"

PY=""
for cand in python3 python; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
    PY="$cand"; break
  fi
done
if [ -z "$PY" ]; then
  echo "Python 3.9 or newer was not found. Please install it (python.org or your package manager)."
  exit 1
fi

if [ ! -x .venv/bin/python ]; then
  echo "Creating virtual environment..."
  "$PY" -m venv .venv
fi

if [ ! -f .venv/.installed ]; then
  echo "Installing dependencies from wheelhouse (offline)..."
  .venv/bin/python -m pip install --no-index --find-links wheelhouse -r requirements.txt
  touch .venv/.installed
fi

exec .venv/bin/python -m app.main
