#!/bin/bash
# ============================================================================
# Configure Super+Space input switching for Wayland
# ============================================================================
# Branches by desktop environment:
#
#   GNOME    — GNOME's Mutter/Wayland intercepts global shortcuts. IBus's
#              own hotkey can't see Super+Space, so we set GNOME's
#              `switch-input-source` keybinding and clear the IBus trigger
#              to avoid conflicts.
#
#   KDE      — KWin does NOT intercept Super+Space by default (KRunner is
#              Alt+Space on Plasma 6), so IBus owns the hotkey directly via
#              the universal `org.freedesktop.ibus.general.hotkey trigger`
#              schema.
#
#   Other    — Same as KDE: let IBus own the hotkey. Works on sway,
#              Hyprland, XFCE+IBus, etc.
#
# An autostart entry is created so the gsetting is re-applied on every
# login (some DEs reset dconf user values during graphical-session start).
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DE="${XDG_CURRENT_DESKTOP:-}"

case "$(echo "$DE" | tr '[:lower:]' '[:upper:]')" in
    *GNOME*)  BACKEND=gnome ;;
    *KDE*)    BACKEND=kde ;;
    *)        BACKEND=other ;;
esac

echo "Configuring input switching for Wayland..."
echo "  Desktop: ${DE:-unknown}  (backend: $BACKEND)"

if [ "$XDG_SESSION_TYPE" = "wayland" ] || [ -n "$WAYLAND_DISPLAY" ]; then
    echo "  Session: Wayland"
else
    echo "  Session: ${XDG_SESSION_TYPE:-X11} — applying anyway (config works on both)"
fi

case "$BACKEND" in
    gnome)
        gsettings set org.gnome.desktop.wm.keybindings switch-input-source "['<Super>space']" 2>/dev/null
        gsettings set org.gnome.desktop.wm.keybindings switch-input-source-backward "['<Shift><Super>space']" 2>/dev/null
        # Clear IBus trigger — conflicts with GNOME's WM-level shortcut
        gsettings set org.freedesktop.ibus.general.hotkey trigger "['']" 2>/dev/null || true
        echo "  Super+Space          = switch input source (GNOME WM)"
        echo "  Shift+Super+Space    = switch back"
        ;;
    kde|other)
        gsettings set org.freedesktop.ibus.general.hotkey trigger "['<Super>space']" 2>/dev/null
        # Don't clobber GNOME's WM keybinding if it was previously set on this user;
        # it's harmless on KDE (GNOME schema isn't read here) but leave it.
        echo "  Super+Space          = switch input source (IBus trigger)"
        if [ "$BACKEND" = "kde" ]; then
            echo "  Note: if KDE has a global shortcut on Super+Space (e.g. KRunner),"
            echo "        unbind it in System Settings → Shortcuts → Global Shortcuts."
        fi
        ;;
esac

# ----------------------------------------------------------------------------
# Autostart: re-apply on every login. Runs this same script — no inline
# bash with escaped quotes (which violates the .desktop spec and is
# rejected by systemd-xdg-autostart-generator).
# ----------------------------------------------------------------------------
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/ibus-avro-wayland-fix.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=iBus Avro Wayland Fix
Comment=Re-apply Super+Space input switching on login (DE-aware)
Exec=$SCRIPT_DIR/setup-wayland.sh
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
EOF

echo "  Autostart entry: $HOME/.config/autostart/ibus-avro-wayland-fix.desktop"
