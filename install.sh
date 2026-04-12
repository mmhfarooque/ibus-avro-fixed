#!/bin/bash
# ============================================================================
# ibus-avro-fixed — One-Command Installer
# ============================================================================
# Installs Avro Phonetic for Bangla typing on Ubuntu/Debian with all
# known bugs fixed:
#   1. Left Shift key fix (keycode 42 was consumed by the engine)
#   2. Right Shift key fix (keycode 54)
#   3. GTK4/libadwaita preferences window (replaces outdated GTK3)
#   4. Wayland Super+Space input switching (X11 key grabs don't work)
#   5. APT hook to re-apply fixes after system updates
#
# Supports: Ubuntu 24.04+, Debian 12+, Linux Mint 21+, Pop!_OS 22.04+
#
# Usage:
#   chmod +x install.sh
#   ./install.sh
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="/usr/share/ibus-avro"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}[OK]${NC} $1"; }
warn() { echo -e "  ${YELLOW}[WARN]${NC} $1"; }
fail() { echo -e "  ${RED}[FAIL]${NC} $1"; }

echo ""
echo "============================================"
echo "  Avro Phonetic for Linux — Fixed Edition"
echo "  Bangla typing with all known bugs fixed"
echo "============================================"
echo ""

if [ "$(id -u)" -eq 0 ]; then
    fail "Do not run as root. The script will use sudo when needed."
    exit 1
fi

# ============================================================================
# Step 1: Install ibus-avro base package if not present
# ============================================================================
echo "[1/6] Checking ibus-avro..."

if dpkg -l ibus-avro &>/dev/null 2>&1; then
    ok "ibus-avro already installed — will apply fixes on top"
    FRESH_INSTALL=false
else
    echo "  Installing ibus-avro and dependencies..."
    sudo apt update -qq
    sudo apt install -y ibus-avro gjs gir1.2-gtk-4.0 gir1.2-adw-1 2>&1 | tail -5
    ok "ibus-avro installed"
    FRESH_INSTALL=true
fi

# Also ensure GTK4/libadwaita bindings are present for the new prefs
sudo apt install -y gir1.2-gtk-4.0 gir1.2-adw-1 2>&1 | tail -2
echo ""

# ============================================================================
# Step 2: Apply Left Shift + Right Shift fix
# ============================================================================
echo "[2/6] Fixing Left Shift / Right Shift bug..."

MAIN_GJS="$INSTALL_DIR/main-gjs.js"
if [ -f "$MAIN_GJS" ]; then
    # Fix keycode 42 (Left Shift): return true → return false
    if grep -q 'if (keycode == 42) {' "$MAIN_GJS"; then
        if grep -q 'keycode == 42) { return true' "$MAIN_GJS"; then
            sudo sed -i 's/if (keycode == 42) { return true; }/if (keycode == 42 || keycode == 54) { return false; }/' "$MAIN_GJS"
            ok "Left Shift + Right Shift fix applied"
        elif grep -q 'keycode == 42.*keycode == 54.*return false' "$MAIN_GJS"; then
            ok "Shift fix already applied"
        else
            ok "Shift key handling already modified"
        fi
    else
        # May be our fork version — check if already fixed
        if grep -q 'keycode == 54.*return false' "$MAIN_GJS"; then
            ok "Shift fix already present (fork version)"
        else
            warn "Could not find keycode 42 handler — file may have changed"
        fi
    fi

    # Disable debug keypress logging
    if grep -q '^\s*print(keyval' "$MAIN_GJS"; then
        sudo sed -i 's|^\(\s*\)print(keyval|\1//print(keyval|' "$MAIN_GJS"
        ok "Disabled keypress debug logging"
    fi
else
    fail "$MAIN_GJS not found"
fi
echo ""

# ============================================================================
# Step 3: Install GTK4 preferences window
# ============================================================================
echo "[3/6] Installing GTK4 preferences window..."

if [ -f "$SCRIPT_DIR/pref.js" ]; then
    sudo cp "$SCRIPT_DIR/pref.js" "$INSTALL_DIR/pref.js"
    ok "GTK4/libadwaita preferences installed"
else
    warn "pref.js not found in $SCRIPT_DIR — skipping GTK4 prefs"
fi
echo ""

# ============================================================================
# Step 4: Create APT hook (re-applies fixes after system updates)
# ============================================================================
echo "[4/6] Installing APT hook for persistence..."

sudo tee /usr/local/bin/fix-ibus-avro.sh > /dev/null << 'PATCHSCRIPT'
#!/bin/bash
# Auto-fix ibus-avro after apt updates
FILE="/usr/share/ibus-avro/main-gjs.js"
if [ -f "$FILE" ]; then
    # Fix Left Shift (keycode 42) and Right Shift (keycode 54)
    if grep -q 'keycode == 42) { return true' "$FILE"; then
        sed -i 's/if (keycode == 42) { return true; }/if (keycode == 42 || keycode == 54) { return false; }/' "$FILE"
    fi
    # Disable debug logging
    sed -i 's|^\(\s*\)print(keyval|\1//print(keyval|' "$FILE"
fi
PATCHSCRIPT

sudo chmod +x /usr/local/bin/fix-ibus-avro.sh

sudo tee /etc/apt/apt.conf.d/99-fix-ibus-avro > /dev/null << 'HOOK'
DPkg::Post-Invoke { "/usr/local/bin/fix-ibus-avro.sh || true"; };
HOOK

ok "APT hook installed — fixes survive apt updates"
echo ""

# ============================================================================
# Step 5: Configure Wayland input switching
# ============================================================================
echo "[5/6] Configuring input switching..."

bash "$SCRIPT_DIR/setup-wayland.sh"
echo ""

# ============================================================================
# Step 6: Restart iBus
# ============================================================================
echo "[6/6] Restarting iBus..."
ibus restart 2>/dev/null || true
sleep 1

# Verify ibus-avro is registered
if ibus list-engine 2>/dev/null | grep -q "avro"; then
    ok "Avro Phonetic engine registered with iBus"
else
    warn "Avro engine not listed — try logging out and back in"
fi
echo ""

# ============================================================================
# Done
# ============================================================================
echo "============================================"
echo -e "  ${GREEN}Installation complete!${NC}"
echo "============================================"
echo ""
echo "  How to use:"
echo "    1. Add 'Bangla (Avro Phonetic)' in Settings → Keyboard → Input Sources"
echo "    2. Press Super+Space to switch between English and Bangla"
echo "    3. Start typing in English — Avro converts to Bangla phonetically"
echo ""
echo "  Preferences:"
echo "    Right-click the iBus tray icon → Preferences"
echo "    Or: gjs --include-path=$INSTALL_DIR $INSTALL_DIR/pref.js --standalone"
echo ""
echo "  What's fixed:"
echo "    - Left Shift key works normally (was broken in upstream)"
echo "    - Right Shift key works normally"
echo "    - Modern GTK4 preferences window"
echo "    - Super+Space switching works on Wayland"
echo "    - Fixes persist across system updates"
echo ""
if [ "$FRESH_INSTALL" = true ]; then
    echo "  NOTE: Log out and log back in for iBus to fully load."
fi
echo ""
