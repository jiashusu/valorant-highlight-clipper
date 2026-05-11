#!/bin/zsh
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt pyinstaller
python3 -m PyInstaller --noconfirm --clean mac/ValorantHighlightClipper.spec

echo "Built: $PROJECT_DIR/dist/ValorantHighlightClipper.app"
