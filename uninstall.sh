#!/bin/bash
# ============================================================================
# ibus-avro-fixed — Uninstall fixes (restores upstream ibus-avro)
# ============================================================================

set -e

# Logging — same log file as the GUI
LOG_DIR="$HOME/.local/share/avro-manager"
LOG_FILE="$LOG_DIR/avro.log"
mkdir -p "$LOG_DIR"
logmsg() { echo "$(date '+%Y-%m-%d %H:%M:%S') [UNINSTALL] $1" >> "$LOG_FILE"; }

echo ""
echo "=== Removing ibus-avro fixes ==="
echo ""
logmsg "=== CLI UNINSTALL STARTING ==="

# Remove APT hook
echo "[1/4] Removing APT hook..."
sudo rm -f /etc/apt/apt.conf.d/99-fix-ibus-avro
sudo rm -f /usr/local/bin/fix-ibus-avro.sh
echo "  Done"

# Remove autostart entry
echo "[2/4] Removing autostart entry..."
rm -f "$HOME/.config/autostart/ibus-avro-wayland-fix.desktop"
echo "  Done"

# Reinstall stock ibus-avro to restore original files
echo "[3/4] Restoring upstream ibus-avro..."
sudo apt install --reinstall -y ibus-avro 2>&1 | tail -3
echo "  Done"

# Restart iBus
echo "[4/4] Restarting iBus..."
ibus restart 2>/dev/null || true

echo ""
echo "=== Uninstall complete ==="
echo "Upstream ibus-avro restored. The Left Shift bug is back."
echo "To reinstall fixes: ./install.sh"
logmsg "=== CLI UNINSTALL COMPLETE ==="
