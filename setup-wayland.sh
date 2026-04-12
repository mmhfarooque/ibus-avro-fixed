#!/bin/bash
# ============================================================================
# Configure Super+Space input switching for GNOME Wayland
# ============================================================================
# iBus uses X11 key grabs which don't work on Wayland. GNOME handles
# input switching natively via gsettings.
#
# This script:
#   1. Sets Super+Space = switch EN → BN
#   2. Sets Shift+Super+Space = switch BN → EN
#   3. Clears iBus trigger (causes conflicts on Wayland)
#   4. Creates autostart entry so it persists across reboots
# ============================================================================

echo "Configuring input switching for Wayland..."

# Check if running on Wayland
if [ "$XDG_SESSION_TYPE" = "wayland" ] || [ -n "$WAYLAND_DISPLAY" ]; then
    echo "  Session: Wayland detected"
else
    echo "  Session: X11 detected — iBus hotkeys should work natively"
    echo "  Applying GNOME shortcuts anyway (works on both X11 and Wayland)"
fi

# Set GNOME input source switching shortcuts
gsettings set org.gnome.desktop.wm.keybindings switch-input-source "['<Super>space']" 2>/dev/null
gsettings set org.gnome.desktop.wm.keybindings switch-input-source-backward "['<Shift><Super>space']" 2>/dev/null

# Clear iBus trigger — doesn't work on Wayland and conflicts if set
gsettings set org.freedesktop.ibus.general.hotkey trigger "['']" 2>/dev/null || true

echo "  Super+Space = switch input source"
echo "  Shift+Super+Space = switch back"

# Create autostart entry to survive reboots and dconf resets
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/ibus-avro-wayland-fix.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=iBus Avro Wayland Fix
Comment=Set Super+Space input switching for Wayland
Exec=bash -c "gsettings set org.gnome.desktop.wm.keybindings switch-input-source \"['<Super>space']\" && gsettings set org.gnome.desktop.wm.keybindings switch-input-source-backward \"['<Shift><Super>space']\""
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
EOF

echo "  Autostart entry created (persists across reboots)"
