#!/usr/bin/env bash
set -e

find_python() {
  for candidate in python3.11 python3.10 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      version="$($candidate -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
      if [ "$version" = "3.10" ] || [ "$version" = "3.11" ]; then
        echo "$candidate"
        return 0
      fi
    fi
  done
  echo "Python 3.10 or 3.11 is required for Basic Pitch/TensorFlow. Install Python 3.11, then run this again." >&2
  return 1
}

PYTHON_CMD="$(find_python)"
"$PYTHON_CMD" -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
npm --prefix frontend install
npm --prefix frontend run build

echo ""
echo "Starting FChord Web App on http://localhost:8000"
echo "Keep this terminal open while using the app. Because naturally servers need to exist to serve things."
echo ""
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --timeout-keep-alive 120
