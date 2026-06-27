#!/bin/bash
# ============================================================================
# Install the Avro Phonetic Manager GUI
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "=== Avro Phonetic Manager — GUI Setup ==="
echo ""

echo "[1/3] Installing GTK4 Python deps + Bangla font..."
# The Bangla Unicode font (fonts-beng / google-noto-sans-bengali-fonts /
# noto-fonts) makes typed Bangla render as glyphs instead of tofu boxes.
if command -v apt &>/dev/null; then
    sudo apt install -y python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 fonts-beng 2>&1 | tail -3
elif command -v dnf &>/dev/null; then
    sudo dnf install -y python3-gobject gtk4 libadwaita google-noto-sans-bengali-fonts 2>&1 | tail -3
elif command -v zypper &>/dev/null; then
    sudo zypper install -y python3-gobject typelib-1_0-Gtk-4_0 typelib-1_0-Adw-1 google-noto-sans-bengali-fonts 2>&1 | tail -3
elif command -v pacman &>/dev/null; then
    sudo pacman -S --needed --noconfirm python-gobject gtk4 libadwaita noto-fonts 2>&1 | tail -3
else
    echo "  Unknown package manager — install PyGObject, GTK4, libadwaita and a Bangla font manually"
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
Name=IBus Avro Manager
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
