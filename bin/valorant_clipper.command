#!/bin/zsh
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

find_python() {
  for candidate in python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
      then
        command -v "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

BASE_PYTHON="$(find_python)"
if [ -z "$BASE_PYTHON" ]; then
  echo "需要 Python 3.10 或更高版本。"
  exit 1
fi

if [ ! -d ".venv" ]; then
  "$BASE_PYTHON" -m venv .venv
elif ! ".venv/bin/python" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
then
  rm -rf .venv
  "$BASE_PYTHON" -m venv .venv
fi

source ".venv/bin/activate"
if ! python - <<'PY'
missing = []
for module in ("fastapi", "uvicorn", "numpy", "PIL"):
    try:
        __import__(module)
    except Exception:
        missing.append(module)
if missing:
    raise SystemExit(1)
PY
then
  python -m pip install -r requirements.txt
fi

export PYTHONPATH="$PROJECT_DIR/src"
(sleep 1.5 && open "http://127.0.0.1:8787") &
python -m uvicorn valorant_clipper.web_app:app --host 127.0.0.1 --port 8787
