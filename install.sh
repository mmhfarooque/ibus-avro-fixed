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

# Logging — same log file as the GUI
LOG_DIR="$HOME/.local/share/avro-manager"
LOG_FILE="$LOG_DIR/avro.log"
mkdir -p "$LOG_DIR"
logmsg() { echo "$(date '+%Y-%m-%d %H:%M:%S') [INSTALL] $1" >> "$LOG_FILE"; }

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}[OK]${NC} $1"; logmsg "OK: $1"; }
warn() { echo -e "  ${YELLOW}[WARN]${NC} $1"; logmsg "WARN: $1"; }
fail() { echo -e "  ${RED}[FAIL]${NC} $1"; logmsg "FAIL: $1"; }

echo ""
echo "============================================"
echo "  Avro Phonetic for Linux — Fixed Edition"
echo "  Bangla typing with all known bugs fixed"
echo "============================================"
echo ""
logmsg "=== INSTALL STARTING === (v$(cat "$SCRIPT_DIR/VERSION" 2>/dev/null || echo 'unknown'))"
logmsg "User: $(whoami) | Session: ${XDG_SESSION_TYPE:-unknown}"

if [ "$(id -u)" -eq 0 ]; then
    fail "Do not run as root. The script will use sudo when needed."
    exit 1
fi

# ============================================================================
# Step 1: Install ibus-avro base package if not present
# ============================================================================
echo "[1/7] Checking ibus-avro..."

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
echo "[2/7] Fixing Left Shift / Right Shift bug..."

MAIN_GJS="$INSTALL_DIR/main-gjs.js"
if [ -f "$MAIN_GJS" ]; then
    # Fix keycode 42 (Left Shift): return true → return false
    # Handles BOTH single-line and multi-line formats
    if grep -q 'keycode == 42' "$MAIN_GJS"; then
        if grep -q 'keycode == 54' "$MAIN_GJS" && grep -A1 'keycode == 42' "$MAIN_GJS" | grep -q 'return false'; then
            ok "Shift fix already applied"
        else
            # Replace the entire block (works for both single-line and multi-line)
            sudo python3 -c "
import re
with open('$MAIN_GJS') as f:
    content = f.read()
# Match both: single-line and multi-line formats
content = re.sub(
    r'(//\s*)?capture the shift key\n\s*if \(keycode == 42\) \{\s*\n?\s*return true;\s*\n?\s*\}',
    'Pass through Left Shift (42) and Right Shift (54)\\n        if (keycode == 42 || keycode == 54) {\\n            return false;\\n        }',
    content
)
# Also handle single-line format
content = content.replace(
    'if (keycode == 42) { return true; }',
    'if (keycode == 42 || keycode == 54) { return false; }'
)
with open('$MAIN_GJS', 'w') as f:
    f.write(content)
"
            if grep -A1 'keycode == 42' "$MAIN_GJS" | grep -q 'return false'; then
                ok "Left Shift + Right Shift fix applied"
            else
                warn "Patch may not have applied correctly — check manually"
            fi
        fi
    else
        warn "Could not find keycode 42 handler — file structure may have changed"
    fi

    # Disable ALL debug print statements (keypress, orientation, candidate clicks)
    if grep -qE '^\s*print\s*\(' "$MAIN_GJS"; then
        # Comment out all active print() calls except the IBus bus error message
        sudo sed -i '/Exiting because IBus/!s|^\(\s*\)print\s*(|\1//print(|' "$MAIN_GJS"
        ok "Disabled debug logging"
    fi
else
    fail "$MAIN_GJS not found"
fi
echo ""

# ============================================================================
# Step 3: Install GTK4 preferences window
# ============================================================================
echo "[3/7] Installing GTK4 preferences window..."

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
echo "[4/7] Installing APT hook for persistence..."

sudo tee /usr/local/bin/fix-ibus-avro.sh > /dev/null << 'PATCHSCRIPT'
#!/bin/bash
# Auto-fix ibus-avro after apt updates
FILE="/usr/share/ibus-avro/main-gjs.js"
if [ -f "$FILE" ]; then
    # Fix Left Shift (keycode 42) and Right Shift (keycode 54)
    # Handles both single-line and multi-line formats
    if grep -q 'keycode == 42' "$FILE" && grep -A1 'keycode == 42' "$FILE" | grep -q 'return true'; then
        python3 -c "
import re
with open('$FILE') as f:
    c = f.read()
c = re.sub(r'(//\s*)?capture the shift key\n\s*if \(keycode == 42\) \{\s*\n?\s*return true;\s*\n?\s*\}',
    'Pass through Left Shift (42) and Right Shift (54)\n        if (keycode == 42 || keycode == 54) {\n            return false;\n        }', c)
c = c.replace('if (keycode == 42) { return true; }', 'if (keycode == 42 || keycode == 54) { return false; }')
with open('$FILE', 'w') as f:
    f.write(c)
"
    fi
    # Disable all debug print statements (except IBus bus error)
    sed -i '/Exiting because IBus/!s|^\(\s*\)print\s*(|\1//print(|' "$FILE"
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
echo "[5/7] Configuring input switching..."

bash "$SCRIPT_DIR/setup-wayland.sh"

# Set GTK_IM_MODULE for Wayland/GNOME 50+ (GNOME doesn't set this automatically)
ENV_DIR="$HOME/.config/environment.d"
mkdir -p "$ENV_DIR"
cat > "$ENV_DIR/10-ibus-avro.conf" << 'ENVEOF'
GTK_IM_MODULE=ibus
QT_IM_MODULE=ibus
XMODIFIERS=@im=ibus
ENVEOF
ok "IBus environment variables set for Wayland"
echo ""

# ============================================================================
# Step 6: Restart iBus
# ============================================================================
echo "[6/7] Restarting iBus..."
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
# ---- Step 7: Install GUI Manager ----
echo "[7/7] Installing GUI Manager..."

# Install Python GTK4 deps (may already be installed from step 1)
sudo apt install -y python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 2>&1 | tail -2

chmod +x "$SCRIPT_DIR/avro-manager.py" 2>/dev/null || true

DESKTOP_FILE="$HOME/.local/share/applications/avro-manager.desktop"
mkdir -p "$HOME/.local/share/applications"
echo "[Desktop Entry]
Type=Application
Name=Avro Phonetic Manager
Comment=Configure Avro Phonetic Bangla input method
Exec=python3 $SCRIPT_DIR/avro-manager.py
Icon=input-keyboard-symbolic
Terminal=false
Categories=Settings;System;
Keywords=avro;bangla;bengali;ibus;phonetic;keyboard;input;" > "$DESKTOP_FILE"

ok "GUI Manager installed — search 'Avro' in app launcher"
echo ""

if [ "$FRESH_INSTALL" = true ]; then
    echo "  NOTE: Log out and log back in for iBus to fully load."
fi
logmsg "=== INSTALL COMPLETE ==="

# Auto-launch the GUI Manager
if [ -f "$SCRIPT_DIR/avro-manager.py" ]; then
    nohup python3 "$SCRIPT_DIR/avro-manager.py" >/dev/null 2>&1 &
    disown
fi

echo ""
echo "  Avro Phonetic Manager is now running."
echo "  Search 'Avro' in your app launcher to open it anytime."
echo ""
