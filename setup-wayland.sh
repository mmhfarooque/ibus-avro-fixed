#!/bin/bash
# ============================================================================
# Configure Super+Space input switching for Wayland
# ============================================================================
# Branches by desktop environment:
#
#   GNOME    — Mutter intercepts global shortcuts on Wayland. Set
#              `org.gnome.desktop.wm.keybindings switch-input-source` to
#              <Super>space and clear IBus's own trigger to avoid conflict.
#
#   KDE      — Bind Meta+Space at the KDE level via kglobalaccel → toggle
#              script (`/usr/local/bin/ibus-avro-toggle`). IBus's own trigger
#              gsetting is X11-era keygrabs and is decorative on Wayland;
#              we don't bother with it. The kglobalaccel binding is applied
#              live via DBus, so it works in the current session — no
#              logout/login required.
#
#   Other    — Best-effort: try the IBus trigger (works on some compositors
#              like sway via fallback IM module).
#
# An autostart entry is created so the GNOME branch's keybinding is
# re-applied on every login (some sessions reset dconf user values during
# graphical-session start). KDE doesn't need autostart — kglobalaccel
# persists shortcuts itself in ~/.config/kglobalshortcutsrc.
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DE="${XDG_CURRENT_DESKTOP:-}"
KDE_SHORTCUT_DESKTOP="com.github.mmhfarooque.ibus-avro-toggle.desktop"

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
        echo "  Super+Space          = switch input source (GNOME WM keybinding)"
        echo "  Shift+Super+Space    = switch back"

        # Re-apply on login via autostart (uses this same script)
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
        ;;

    kde)
        # Clear the (decorative) IBus trigger in case v2.5.0 / v2.5.1 set it.
        gsettings set org.freedesktop.ibus.general.hotkey trigger "['']" 2>/dev/null || true

        # Register IBus as the Plasma 6 Wayland Virtual Keyboard. Without
        # this, KWin doesn't route IM events through IBus, and the user
        # sees a notification asking them to do it manually via
        # systemsettings → Input & Output → Keyboard → Virtual Keyboard.
        IBUS_VK_DESKTOP=$(ls /usr/share/applications/org.freedesktop.IBus.Panel.Wayland.*.desktop 2>/dev/null | head -1)
        if [ -n "$IBUS_VK_DESKTOP" ] && command -v kwriteconfig6 >/dev/null 2>&1; then
            kwriteconfig6 --file kwinrc --group Wayland --key InputMethod "$IBUS_VK_DESKTOP" >/dev/null 2>&1 || true
            qdbus6 org.kde.KWin /KWin reconfigure >/dev/null 2>&1 || true
            echo "  Plasma Virtual Keyboard: IBus ($(basename "$IBUS_VK_DESKTOP"))"
        fi

        # Ensure preload-engines includes both English keyboard + Avro.
        # KDE's input switcher / IBus tray needs at least one engine listed
        # here to show anything; on a fresh install with no prior config,
        # the list is empty.
        CURRENT_PRELOAD=$(gsettings get org.freedesktop.ibus.general preload-engines 2>/dev/null)
        if ! echo "$CURRENT_PRELOAD" | grep -q "ibus-avro"; then
            gsettings set org.freedesktop.ibus.general preload-engines "['xkb:us::eng', 'ibus-avro']" 2>/dev/null || true
            echo "  preload-engines: ['xkb:us::eng', 'ibus-avro']"
        fi

        # 1. Install user-level desktop entry pointing at the toggle script.
        mkdir -p "$HOME/.local/share/applications"
        cat > "$HOME/.local/share/applications/$KDE_SHORTCUT_DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=Toggle Avro / English (IBus)
Comment=Switch between Bangla Avro Phonetic and English input
Exec=/usr/local/bin/ibus-avro-toggle
Icon=input-keyboard-symbolic
NoDisplay=true
Terminal=false
StartupNotify=false
EOF

        # 2. Live-register the Meta+Space shortcut with kglobalaccel via DBus.
        #    Action ID: [componentUniqueName, actionName, friendlyComp, friendlyAction].
        #    Meta+Space = Qt::Key_Space (0x20) | Qt::MetaModifier (0x10000000) = 268435488
        if command -v gdbus >/dev/null 2>&1; then
            ACTION_ID="['$KDE_SHORTCUT_DESKTOP','_launch','Toggle Avro/English Input','Toggle Avro/English Input']"
            gdbus call --session --dest org.kde.kglobalaccel \
                --object-path /kglobalaccel \
                --method org.kde.KGlobalAccel.doRegister "$ACTION_ID" >/dev/null 2>&1 || true
            gdbus call --session --dest org.kde.kglobalaccel \
                --object-path /kglobalaccel \
                --method org.kde.KGlobalAccel.setShortcut "$ACTION_ID" '[268435488]' 4 >/dev/null 2>&1 || true
        fi

        # 3. Also persist via kwriteconfig6 (defensive — kglobalaccel writes
        #    this itself, but if DBus call failed we still have a valid file
        #    that takes effect on next login).
        if command -v kwriteconfig6 >/dev/null 2>&1; then
            kwriteconfig6 --file kglobalshortcutsrc \
                --group "$KDE_SHORTCUT_DESKTOP" \
                --key "_k_friendly_name" "Toggle Avro/English Input" >/dev/null 2>&1 || true
            kwriteconfig6 --file kglobalshortcutsrc \
                --group "$KDE_SHORTCUT_DESKTOP" \
                --key "_launch" "Meta+Space,none,Toggle Avro/English Input" >/dev/null 2>&1 || true
        fi

        echo "  Super+Space          = toggle Avro / English (KDE kglobalaccel)"
        echo "  Mechanism: ~/.local/share/applications/$KDE_SHORTCUT_DESKTOP"
        echo "             → /usr/local/bin/ibus-avro-toggle"
        echo "  Note: works immediately, no logout required."
        ;;

    other)
        # Best-effort: set the IBus trigger. Works on some compositors
        # (e.g. sway with the right IM module). Won't fire on KDE/GNOME
        # Wayland but those have their own branches above.
        gsettings set org.freedesktop.ibus.general.hotkey trigger "['<Super>space']" 2>/dev/null
        echo "  Super+Space          = IBus trigger (best-effort on this DE)"
        echo "  If it doesn't switch, your compositor needs a DE-specific binding."
        ;;
esac
