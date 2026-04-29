#!/bin/bash
# ============================================================================
# ibus-avro-toggle — switch between Avro Phonetic and English
# ============================================================================
# Installed to /usr/local/bin/ibus-avro-toggle by install.sh.
# Bound to Meta+Space on KDE Plasma via kglobalaccel (see setup-wayland.sh
# KDE branch). On GNOME this script is unused — gnome-shell handles the
# WM-level shortcut directly.
#
# Two-engine toggle (ibus-avro ↔ xkb:us::eng). If you have more engines,
# use the IBus tray menu for fine-grained control.
# ============================================================================

case "$(ibus engine 2>/dev/null)" in
    ibus-avro)
        ibus engine xkb:us::eng
        ;;
    *)
        ibus engine ibus-avro
        ;;
esac
