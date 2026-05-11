#!/bin/zsh
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
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
