#!/bin/bash
# AnberHex installer dla Anbernic RG40XX V
# Uruchom jako root na konsoli (przez SSH lub terminal)
set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APPS_DIR="/mnt/mmc/Roms/APPS"
APP_DIR="$APPS_DIR/anberhex"
IMGS_DIR="$APPS_DIR/Imgs"

echo "=== AnberHex install ==="

# 1. SDL2 app + launcher
mkdir -p "$APP_DIR"
cp "$REPO_DIR/app/main.py"   "$APP_DIR/main.py"
cp "$REPO_DIR/app/AnberHex.sh" "$APPS_DIR/AnberHex.sh"
chmod +x "$APPS_DIR/AnberHex.sh" "$APP_DIR/main.py"
echo "✓ App skopiowane do $APP_DIR"

# 2. Ikona
mkdir -p "$IMGS_DIR"
if [ -f "$REPO_DIR/AnberHex.png" ]; then
    cp "$REPO_DIR/AnberHex.png" "$IMGS_DIR/AnberHex.png"
    echo "✓ Ikona w $IMGS_DIR/AnberHex.png"
fi

# 3. Zależności
python3 -c "import sdl2" 2>/dev/null || echo "⚠️  brak pysdl2 — pip install pysdl2"
python3 -c "import PIL"  2>/dev/null || echo "⚠️  brak Pillow — pip install Pillow"
python3 -c "import evdev" 2>/dev/null || echo "⚠️  brak evdev — pip install evdev"

# 4. Self-test logiki
echo "--- self-test ---"
python3 "$APP_DIR/main.py" --selftest || true

echo ""
echo "Zainstalowane. Uruchom 'AnberHex' z App Center."
