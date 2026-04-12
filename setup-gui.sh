#!/bin/bash
# ============================================================================
# Install the Avro Phonetic Manager GUI
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "=== Avro Phonetic Manager — GUI Setup ==="
echo ""

echo "[1/3] Installing GTK4 Python dependencies..."
if command -v apt &>/dev/null; then
    sudo apt install -y python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 2>&1 | tail -3
elif command -v dnf &>/dev/null; then
    sudo dnf install -y python3-gobject gtk4 libadwaita 2>&1 | tail -3
elif command -v pacman &>/dev/null; then
    sudo pacman -S --needed --noconfirm python-gobject gtk4 libadwaita 2>&1 | tail -3
else
    echo "  Unknown package manager — install python3-gi, GTK4, libadwaita manually"
fi
echo ""

echo "[2/3] Setting up GUI..."
chmod +x "$SCRIPT_DIR/avro-manager.py"
echo ""

echo "[3/3] Creating desktop shortcut..."
DESKTOP_FILE="$HOME/.local/share/applications/avro-manager.desktop"
mkdir -p "$HOME/.local/share/applications"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Application
Name=Avro Phonetic Manager
Comment=Configure Avro Phonetic Bangla input method
Exec=python3 $SCRIPT_DIR/avro-manager.py
Icon=input-keyboard-symbolic
Terminal=false
Categories=Settings;System;
Keywords=avro;bangla;bengali;ibus;phonetic;keyboard;input;
EOF

echo ""
echo "=== Setup complete ==="
echo ""
echo "  Launch: python3 $SCRIPT_DIR/avro-manager.py"
echo "  Or search 'Avro' in your app launcher"
echo ""
