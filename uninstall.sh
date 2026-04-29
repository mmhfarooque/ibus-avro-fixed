#!/bin/bash
# ============================================================================
# ibus-avro-fixed — Total uninstall (removes IBus entirely)
# ============================================================================
# Use this when you want a fully clean system: no IBus packages, no patches,
# no user state. Suitable as the "before" step of a fresh `bash install.sh`
# smoke test.
#
# What this removes:
#   - All IBus apt packages: ibus, ibus-avro, ibus-data, ibus-gtk3, ibus-gtk4
#     (and orphans pulled in only by them)
#   - Our patches: APT hook, fix-ibus-avro.sh, ibus-avro-toggle, GUI launcher
#   - User state: ~/.config/ibus, ~/.local/share/avro-manager, autostart,
#     environment.d/10-ibus-avro.conf, dconf /desktop/ibus/
#   - KDE: kglobalaccel Meta+Space binding (the toggle action)
#   - Running ibus daemon and helper processes
#
# Sudo is used for apt + /etc/ + /usr/local/bin/ ops. Run from a normal
# terminal so sudo can prompt for your password.
#
# After this script finishes:
#   - `which ibus` → not found
#   - No IBus tray icon
#   - System ready for `bash install.sh` (which will pull ibus back as a dep)
# ============================================================================

set -u

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}[OK]${NC} $1"; }
warn() { echo -e "  ${YELLOW}[WARN]${NC} $1"; }
fail() { echo -e "  ${RED}[FAIL]${NC} $1"; }

echo ""
echo "============================================"
echo "  Avro Phonetic for Linux — Total Uninstall"
echo "============================================"
echo ""

if [ "$(id -u)" -eq 0 ]; then
    fail "Do not run as root. The script will use sudo when needed."
    exit 1
fi

# Detect DE for the kglobalaccel unbind step
case "$(echo "${XDG_CURRENT_DESKTOP:-}" | tr '[:lower:]' '[:upper:]')" in
    *KDE*)    CURRENT_DE=kde ;;
    *GNOME*)  CURRENT_DE=gnome ;;
    *)        CURRENT_DE=other ;;
esac

# ============================================================================
# Step 1: User-level cleanup (no sudo)
# ============================================================================
echo "[1/5] Removing user-level configs..."
rm -f "$HOME/.config/autostart/ibus-avro-wayland-fix.desktop"
rm -f "$HOME/.config/environment.d/10-ibus-avro.conf"
rm -f "$HOME/.local/share/applications/avro-manager.desktop"
rm -f "$HOME/.local/share/applications/com.github.mmhfarooque.ibus-avro-toggle.desktop"
rm -f "$HOME/.local/bin/ibus-avro-toggle"
rm -rf "$HOME/.config/ibus"
rm -rf "$HOME/.local/share/avro-manager"

# Reset IBus dconf settings (no-op if schemas aren't installed)
dconf reset -f /desktop/ibus/ 2>/dev/null || true
ok "User configs removed"

# ============================================================================
# Step 2: KDE kglobalaccel unbind (no sudo)
# ============================================================================
if [ "$CURRENT_DE" = "kde" ]; then
    echo "[2/5] Unbinding KDE Meta+Space toggle..."
    if command -v gdbus >/dev/null 2>&1; then
        ACTION_ID="['com.github.mmhfarooque.ibus-avro-toggle.desktop','_launch','Toggle Avro/English Input','Toggle Avro/English Input']"
        gdbus call --session --dest org.kde.kglobalaccel \
            --object-path /kglobalaccel \
            --method org.kde.KGlobalAccel.unRegister "$ACTION_ID" >/dev/null 2>&1 || true
    fi
    if command -v kwriteconfig6 >/dev/null 2>&1; then
        kwriteconfig6 --file kglobalshortcutsrc \
            --group "com.github.mmhfarooque.ibus-avro-toggle.desktop" \
            --key "_launch" --delete >/dev/null 2>&1 || true
        kwriteconfig6 --file kglobalshortcutsrc \
            --group "com.github.mmhfarooque.ibus-avro-toggle.desktop" \
            --key "_k_friendly_name" --delete >/dev/null 2>&1 || true
    fi
    ok "kglobalaccel binding removed"
else
    echo "[2/5] Skipped (not KDE — no kglobalaccel binding to remove)"
fi

# ============================================================================
# Step 3: Remove APT hook + system scripts (sudo)
# ============================================================================
echo "[3/5] Removing system scripts (sudo)..."
sudo rm -f /etc/apt/apt.conf.d/99-fix-ibus-avro \
           /usr/local/bin/fix-ibus-avro.sh \
           /usr/local/bin/ibus-avro-toggle
ok "APT hook + fix scripts removed"

# ============================================================================
# Step 4: Purge IBus packages (sudo)
# ============================================================================
echo "[4/5] Purging IBus packages..."
# `--purge` removes config files too; `2>/dev/null || true` so we don't
# crash if some packages aren't installed.
sudo DEBIAN_FRONTEND=noninteractive apt-get remove --purge -y \
    ibus-avro ibus ibus-data ibus-gtk3 ibus-gtk4 2>&1 \
    | grep -E "^(Removing|Purging|The following)" || true
sudo DEBIAN_FRONTEND=noninteractive apt-get autoremove --purge -y 2>&1 \
    | grep -E "^(Removing|Purging)" || true
ok "IBus packages purged"

# ============================================================================
# Step 5: Kill leftover daemon/helper processes
# ============================================================================
echo "[5/5] Killing leftover IBus processes..."
# Even after package removal, helpers loaded into memory keep running until
# explicitly killed. Without this, the tray icon may linger and a re-install
# can pick up stale state.
pkill -f 'ibus-daemon|ibus-ui-gtk3|ibus-dconf|ibus-extension|ibus-x11|ibus-portal|ibus-engine' 2>/dev/null || true
sleep 1
if pgrep -f 'ibus-daemon|ibus-ui-gtk3' >/dev/null 2>&1; then
    warn "Some IBus processes are still running — try logging out if the tray icon persists"
else
    ok "All IBus processes terminated"
fi

# ============================================================================
# Step 6: Remove the source directory itself (this script's own home)
# ============================================================================
# Without this, the cloned repo lingers and blocks a fresh `git clone` to
# the same path. "Uninstall like it never existed" means the source tree
# goes too. Bash holds the script in memory once started, so deleting the
# file under our feet is safe; we cd out first so the shell's CWD is valid.
echo ""
echo -e "  ${GREEN}Uninstall complete.${NC} IBus is gone."
echo ""
echo "Removing source directory: $SCRIPT_DIR"
cd / && rm -rf "$SCRIPT_DIR"
echo ""
