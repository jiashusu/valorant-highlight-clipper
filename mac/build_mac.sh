#!/bin/zsh
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

BUILD_SHA="${APP_BUILD_SHA:-}"
if [ -z "$BUILD_SHA" ] && command -v git >/dev/null 2>&1; then
  BUILD_SHA="$(git rev-parse HEAD 2>/dev/null || true)"
fi
if [ -z "$BUILD_SHA" ]; then
  BUILD_SHA="unknown"
fi
BUILD_DATE="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
cat > src/valorant_clipper/build_info.py <<PY
BUILD_SHA = "${BUILD_SHA}"
BUILD_DATE = "${BUILD_DATE}"
PY

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt pyinstaller
python3 -m PyInstaller --noconfirm --clean mac/ValorantHighlightClipper.spec

echo "Built: $PROJECT_DIR/dist/ValorantHighlightClipper.app"
