#!/usr/bin/env python3
"""
Avro Phonetic Manager — Full GUI for ibus-avro-fixed.

Status, input switching, typing settings, fix management, and maintenance.
Uses GTK4 + libadwaita for native GNOME look.
"""

import gi
import os
import re
import signal
import subprocess
import threading

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk

APP_ID = "com.github.mmhfarooque.avro-manager"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INSTALL_DIR = "/usr/share/ibus-avro"
MAIN_GJS = os.path.join(INSTALL_DIR, "main-gjs.js")

def get_version():
    try:
        with open(os.path.join(SCRIPT_DIR, "VERSION")) as f:
            return f.read().strip()
    except FileNotFoundError:
        return "dev"

APP_VERSION = get_version()


# ============================================================================
# Helper functions
# ============================================================================

def run_cmd(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return 1, "", str(e)


def run_as_root(cmd_str):
    return run_cmd(["pkexec", "bash", "-c", cmd_str], timeout=60)


def is_ibus_running():
    rc, out, _ = run_cmd(["pgrep", "-x", "ibus-daemon"])
    return rc == 0


def is_avro_installed():
    return os.path.exists(MAIN_GJS)


def is_avro_registered():
    rc, out, _ = run_cmd(["ibus", "list-engine"])
    return "avro" in out.lower() if rc == 0 else False


def get_session_type():
    session = os.environ.get("XDG_SESSION_TYPE", "")
    if session:
        return session
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    return "x11"


def get_current_input_sources():
    rc, out, _ = run_cmd([
        "gsettings", "get", "org.gnome.desktop.input-sources", "sources"
    ])
    return out if rc == 0 else "Unknown"


def is_shift_fix_applied():
    """Check if Left Shift bug is fixed."""
    try:
        with open(MAIN_GJS) as f:
            content = f.read()
            # Fixed if keycode 42 returns false (or includes 54)
            if "keycode == 42" in content:
                return "return false" in content.split("keycode == 42")[1].split("\n")[0]
            return False
    except FileNotFoundError:
        return False


def is_debug_disabled():
    """Check if debug print statements are commented out."""
    try:
        with open(MAIN_GJS) as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("print(") or stripped.startswith("print ("):
                    if "Exiting because" not in line:
                        return False
            return True
    except FileNotFoundError:
        return False


def is_apt_hook_installed():
    return os.path.exists("/etc/apt/apt.conf.d/99-fix-ibus-avro")


def is_wayland_switching_configured():
    rc, out, _ = run_cmd([
        "gsettings", "get", "org.gnome.desktop.wm.keybindings", "switch-input-source"
    ])
    return "<Super>space" in out if rc == 0 else False


def is_gtk4_prefs_installed():
    """Check if pref.js has GTK4 imports."""
    pref_path = os.path.join(INSTALL_DIR, "pref.js")
    try:
        with open(pref_path) as f:
            content = f.read()
            return "Adw" in content and "4.0" in content
    except FileNotFoundError:
        return False


def get_avro_settings():
    """Read current Avro GSettings."""
    settings = {}
    schema = "com.omicronlab.avro"
    for key in ["switch-preview", "switch-dict", "switch-newline"]:
        rc, out, _ = run_cmd(["gsettings", "get", schema, key])
        settings[key] = out.strip() == "true" if rc == 0 else False
    for key in ["lutable-size", "cboxorient"]:
        rc, out, _ = run_cmd(["gsettings", "get", schema, key])
        try:
            settings[key] = int(out.strip())
        except (ValueError, AttributeError):
            settings[key] = 15 if key == "lutable-size" else 0
    return settings


def set_avro_setting(key, value):
    schema = "com.omicronlab.avro"
    if isinstance(value, bool):
        val_str = "true" if value else "false"
    else:
        val_str = str(value)
    run_cmd(["gsettings", "set", schema, key, val_str])


def get_switch_shortcut():
    rc, out, _ = run_cmd([
        "gsettings", "get", "org.gnome.desktop.wm.keybindings", "switch-input-source"
    ])
    if rc == 0 and out:
        # Parse ['<Super>space'] format
        match = re.search(r"'([^']+)'", out)
        return match.group(1) if match else out
    return "Not set"


# ============================================================================
# Main Application
# ============================================================================

class AvroManagerApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        self.win = AvroManagerWindow(application=app)
        self.win.present()


class AvroManagerWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title(f"Avro Phonetic Manager v{APP_VERSION}")
        self.set_default_size(640, 820)

        # Main layout
        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)

        # Header bar
        header = Adw.HeaderBar()
        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Refresh")
        refresh_btn.connect("clicked", lambda _: self.refresh_all())
        header.pack_end(refresh_btn)
        toolbar_view.add_top_bar(header)

        # Toast overlay
        self.toast_overlay = Adw.ToastOverlay()
        toolbar_view.set_content(self.toast_overlay)

        # Scrollable content
        scroll = Gtk.ScrolledWindow(vexpand=True)
        self.toast_overlay.set_child(scroll)

        main_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=0,
            margin_start=16, margin_end=16, margin_top=8, margin_bottom=16,
        )
        scroll.set_child(main_box)

        # Build sections
        self.build_status_section(main_box)
        self.build_switching_section(main_box)
        self.build_typing_section(main_box)
        self.build_fixes_section(main_box)
        self.build_maintenance_section(main_box)

        # Load data
        self.refresh_all()

    def show_toast(self, msg):
        self.toast_overlay.add_toast(Adw.Toast(title=msg, timeout=3))

    # ========================================================================
    # Status Section
    # ========================================================================

    def build_status_section(self, parent):
        group = Adw.PreferencesGroup(title="Status")
        parent.append(group)

        self.status_ibus = Adw.ActionRow(title="IBus Daemon", subtitle="Checking...")
        self.status_ibus.add_prefix(Gtk.Image.new_from_icon_name("system-run-symbolic"))
        group.add(self.status_ibus)

        self.status_avro = Adw.ActionRow(title="Avro Engine", subtitle="Checking...")
        self.status_avro.add_prefix(Gtk.Image.new_from_icon_name("input-keyboard-symbolic"))
        group.add(self.status_avro)

        self.status_session = Adw.ActionRow(title="Session Type", subtitle="Checking...")
        self.status_session.add_prefix(Gtk.Image.new_from_icon_name("computer-symbolic"))
        group.add(self.status_session)

        self.status_sources = Adw.ActionRow(title="Input Sources", subtitle="Checking...")
        self.status_sources.add_prefix(Gtk.Image.new_from_icon_name("preferences-desktop-locale-symbolic"))
        group.add(self.status_sources)

    # ========================================================================
    # Input Switching Section
    # ========================================================================

    def build_switching_section(self, parent):
        group = Adw.PreferencesGroup(
            title="Input Switching",
            description="Keyboard shortcut to switch between English and Bangla",
        )
        parent.append(group)

        self.switch_shortcut_row = Adw.ActionRow(
            title="Switch Shortcut",
            subtitle="Loading...",
        )
        self.switch_shortcut_row.add_prefix(Gtk.Image.new_from_icon_name("input-keyboard-symbolic"))
        group.add(self.switch_shortcut_row)

        self.switch_back_row = Adw.ActionRow(
            title="Switch Back",
            subtitle="Shift + Super + Space",
        )
        self.switch_back_row.add_prefix(Gtk.Image.new_from_icon_name("go-previous-symbolic"))
        group.add(self.switch_back_row)

        # Apply Wayland switching button
        apply_row = Adw.ActionRow(title="")
        self.wayland_btn = Gtk.Button(
            label="Configure Super+Space Switching",
            css_classes=["suggested-action"], valign=Gtk.Align.CENTER,
        )
        self.wayland_btn.connect("clicked", self.on_configure_switching)
        apply_row.add_suffix(self.wayland_btn)
        group.add(apply_row)

    def on_configure_switching(self, btn):
        run_cmd(["gsettings", "set", "org.gnome.desktop.wm.keybindings",
                 "switch-input-source", "['<Super>space']"])
        run_cmd(["gsettings", "set", "org.gnome.desktop.wm.keybindings",
                 "switch-input-source-backward", "['<Shift><Super>space']"])
        run_cmd(["gsettings", "set", "org.freedesktop.ibus.general.hotkey",
                 "trigger", "['']"])

        # Create autostart
        autostart_dir = os.path.expanduser("~/.config/autostart")
        os.makedirs(autostart_dir, exist_ok=True)
        with open(os.path.join(autostart_dir, "ibus-avro-wayland-fix.desktop"), "w") as f:
            f.write('[Desktop Entry]\nType=Application\nName=iBus Avro Wayland Fix\n')
            f.write("Exec=bash -c \"gsettings set org.gnome.desktop.wm.keybindings ")
            f.write("switch-input-source \\\"['<Super>space']\\\" && gsettings set ")
            f.write("org.gnome.desktop.wm.keybindings switch-input-source-backward ")
            f.write("\\\"['<Shift><Super>space']\\\"\"\n")
            f.write("Hidden=false\nNoDisplay=true\nX-GNOME-Autostart-enabled=true\n")

        self.show_toast("Super+Space switching configured")
        self.refresh_switching()

    def refresh_switching(self):
        shortcut = get_switch_shortcut()
        self.switch_shortcut_row.set_subtitle(shortcut)

    # ========================================================================
    # Typing Settings Section
    # ========================================================================

    def build_typing_section(self, parent):
        group = Adw.PreferencesGroup(
            title="Typing Settings",
            description="Avro Phonetic engine behaviour",
        )
        parent.append(group)

        # Preview window
        self.preview_row = Adw.SwitchRow(
            title="Preview Window",
            subtitle="Show suggestion preview while typing",
        )
        self.preview_row.connect("notify::active", self._on_preview_changed)
        group.add(self.preview_row)

        # Enter closes preview
        self.newline_row = Adw.SwitchRow(
            title="Enter Closes Preview Only",
            subtitle="Enter commits text without inserting a new line",
        )
        group.add(self.newline_row)

        # Dictionary suggestions
        self.dict_row = Adw.SwitchRow(
            title="Dictionary Suggestions",
            subtitle="Show Bangla word suggestions from dictionary",
        )
        group.add(self.dict_row)

        # Max suggestions
        self.sug_adj = Gtk.Adjustment(value=15, lower=5, upper=15, step_increment=1)
        self.sug_row = Adw.SpinRow(
            title="Max Suggestions",
            subtitle="Maximum dictionary suggestions (5-15)",
            adjustment=self.sug_adj,
        )
        group.add(self.sug_row)

        # Orientation
        self.orient_row = Adw.ActionRow(
            title="Suggestion List Orientation",
            subtitle="Direction of the candidate list",
        )
        self.orient_dropdown = Gtk.DropDown(
            model=Gtk.StringList.new(["Horizontal", "Vertical"]),
            valign=Gtk.Align.CENTER,
        )
        self.orient_row.add_suffix(self.orient_dropdown)
        group.add(self.orient_row)

        # Apply button
        apply_row = Adw.ActionRow(title="")
        self.typing_apply_btn = Gtk.Button(
            label="Apply Typing Settings",
            css_classes=["suggested-action"], valign=Gtk.Align.CENTER,
        )
        self.typing_apply_btn.connect("clicked", self.on_apply_typing)
        apply_row.add_suffix(self.typing_apply_btn)
        group.add(apply_row)

    def _on_preview_changed(self, row, _):
        active = row.get_active()
        self.newline_row.set_sensitive(active)
        self.dict_row.set_sensitive(active)
        self.sug_row.set_sensitive(active)
        self.orient_row.set_sensitive(active)

    def on_apply_typing(self, btn):
        set_avro_setting("switch-preview", self.preview_row.get_active())
        set_avro_setting("switch-newline", self.newline_row.get_active())
        set_avro_setting("switch-dict", self.dict_row.get_active())
        set_avro_setting("lutable-size", int(self.sug_adj.get_value()))
        set_avro_setting("cboxorient", self.orient_dropdown.get_selected())
        self.show_toast("Typing settings applied")

    # ========================================================================
    # Fixes Status Section
    # ========================================================================

    def build_fixes_section(self, parent):
        group = Adw.PreferencesGroup(
            title="Fix Status",
            description="Status of all applied bug fixes",
        )
        parent.append(group)

        self.fix_shift = Adw.ActionRow(title="Left/Right Shift Fix", subtitle="Checking...")
        self.fix_shift.add_prefix(Gtk.Image.new_from_icon_name("keyboard-symbolic"))
        group.add(self.fix_shift)

        self.fix_debug = Adw.ActionRow(title="Debug Logging Disabled", subtitle="Checking...")
        self.fix_debug.add_prefix(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
        group.add(self.fix_debug)

        self.fix_gtk4 = Adw.ActionRow(title="GTK4 Preferences", subtitle="Checking...")
        self.fix_gtk4.add_prefix(Gtk.Image.new_from_icon_name("preferences-system-symbolic"))
        group.add(self.fix_gtk4)

        self.fix_wayland = Adw.ActionRow(title="Wayland Switching", subtitle="Checking...")
        self.fix_wayland.add_prefix(Gtk.Image.new_from_icon_name("network-wireless-symbolic"))
        group.add(self.fix_wayland)

        self.fix_apt = Adw.ActionRow(title="APT Hook (Persistence)", subtitle="Checking...")
        self.fix_apt.add_prefix(Gtk.Image.new_from_icon_name("security-high-symbolic"))
        group.add(self.fix_apt)

        # Apply all fixes button
        fix_row = Adw.ActionRow(title="")
        self.apply_all_btn = Gtk.Button(
            label="Apply All Fixes", css_classes=["suggested-action"],
            valign=Gtk.Align.CENTER,
        )
        self.apply_all_btn.connect("clicked", self.on_apply_all_fixes)
        fix_row.add_suffix(self.apply_all_btn)
        group.add(fix_row)

    def on_apply_all_fixes(self, btn):
        btn.set_sensitive(False)
        btn.set_label("Applying...")
        self.show_toast("Applying all fixes...")

        def do_apply():
            script = os.path.join(SCRIPT_DIR, "install.sh")
            rc, out, err = run_cmd(["bash", script], timeout=120)
            GLib.idle_add(self._apply_done, rc == 0)
            return False

        threading.Thread(target=do_apply, daemon=True).start()

    def _apply_done(self, success):
        self.apply_all_btn.set_sensitive(True)
        self.apply_all_btn.set_label("Apply All Fixes")
        self.show_toast("All fixes applied!" if success else "Some fixes failed — check terminal")
        self.refresh_all()
        return False

    # ========================================================================
    # Maintenance Section
    # ========================================================================

    def build_maintenance_section(self, parent):
        group = Adw.PreferencesGroup(title="Maintenance")
        parent.append(group)

        # Restart iBus
        restart_row = Adw.ActionRow(
            title="Restart IBus",
            subtitle="Restart the input method framework",
        )
        restart_row.add_prefix(Gtk.Image.new_from_icon_name("view-refresh-symbolic"))
        restart_btn = Gtk.Button(label="Restart", valign=Gtk.Align.CENTER)
        restart_btn.connect("clicked", self.on_restart_ibus)
        restart_row.add_suffix(restart_btn)
        group.add(restart_row)

        # Open Preferences
        pref_row = Adw.ActionRow(
            title="Avro Preferences",
            subtitle="Open the Avro Phonetic preferences dialog",
        )
        pref_row.add_prefix(Gtk.Image.new_from_icon_name("preferences-system-symbolic"))
        pref_btn = Gtk.Button(label="Open", valign=Gtk.Align.CENTER)
        pref_btn.connect("clicked", self.on_open_prefs)
        pref_row.add_suffix(pref_btn)
        group.add(pref_row)

        # Add input source
        source_row = Adw.ActionRow(
            title="Add Bangla Input Source",
            subtitle="Open GNOME Keyboard Settings to add Avro Phonetic",
        )
        source_row.add_prefix(Gtk.Image.new_from_icon_name("preferences-desktop-keyboard-symbolic"))
        source_btn = Gtk.Button(label="Open Settings", valign=Gtk.Align.CENTER)
        source_btn.connect("clicked", self.on_open_keyboard_settings)
        source_row.add_suffix(source_btn)
        group.add(source_row)

        # Uninstall
        uninstall_row = Adw.ActionRow(
            title="Restore Upstream",
            subtitle="Remove all fixes and restore stock ibus-avro",
        )
        uninstall_row.add_prefix(Gtk.Image.new_from_icon_name("user-trash-symbolic"))
        uninstall_btn = Gtk.Button(
            label="Restore", css_classes=["destructive-action"],
            valign=Gtk.Align.CENTER,
        )
        uninstall_btn.connect("clicked", self.on_uninstall)
        uninstall_row.add_suffix(uninstall_btn)
        group.add(uninstall_row)

    def on_restart_ibus(self, btn):
        run_cmd(["ibus", "restart"])
        self.show_toast("IBus restarted")
        GLib.timeout_add(2000, lambda: (self.refresh_all(), False)[-1])

    def on_open_prefs(self, btn):
        pkgdir = INSTALL_DIR
        pref_js = os.path.join(pkgdir, "pref.js")
        if os.path.exists(pref_js):
            subprocess.Popen([
                "/usr/bin/env", "gjs",
                f"--include-path={pkgdir}", pref_js, "--standalone"
            ])
            self.show_toast("Preferences window opened")
        else:
            self.show_toast("pref.js not found — run Apply All Fixes first")

    def on_open_keyboard_settings(self, btn):
        subprocess.Popen(["gnome-control-center", "keyboard"])

    def on_uninstall(self, btn):
        dialog = Adw.AlertDialog(
            heading="Restore upstream ibus-avro?",
            body="This removes all fixes (Shift fix, GTK4 prefs, Wayland switching, APT hook). "
                 "The Left Shift bug will come back.",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("restore", "Restore Upstream")
        dialog.set_response_appearance("restore", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_uninstall_confirmed)
        dialog.present(self)

    def _on_uninstall_confirmed(self, dialog, response):
        if response != "restore":
            return

        def do_uninstall():
            script = os.path.join(SCRIPT_DIR, "uninstall.sh")
            rc, _, err = run_cmd(["bash", script], timeout=120)
            def _done():
                self.show_toast("Upstream restored" if rc == 0 else f"Failed: {err[:60]}")
                self.refresh_all()
                return False
            GLib.idle_add(_done)

        threading.Thread(target=do_uninstall, daemon=True).start()

    # ========================================================================
    # Refresh all
    # ========================================================================

    def refresh_all(self):
        def do_refresh():
            data = {
                "ibus": is_ibus_running(),
                "avro": is_avro_installed(),
                "registered": is_avro_registered(),
                "session": get_session_type(),
                "sources": get_current_input_sources(),
                "shortcut": get_switch_shortcut(),
                "shift_fix": is_shift_fix_applied(),
                "debug_off": is_debug_disabled(),
                "gtk4_prefs": is_gtk4_prefs_installed(),
                "wayland": is_wayland_switching_configured(),
                "apt_hook": is_apt_hook_installed(),
                "settings": get_avro_settings(),
            }
            GLib.idle_add(self._apply_refresh, data)
            return False

        threading.Thread(target=do_refresh, daemon=True).start()

    def _apply_refresh(self, d):
        # Status
        self.status_ibus.set_subtitle("Running" if d["ibus"] else "Not running")
        if d["avro"] and d["registered"]:
            self.status_avro.set_subtitle("Installed and registered")
        elif d["avro"]:
            self.status_avro.set_subtitle("Installed (not yet registered — restart IBus)")
        else:
            self.status_avro.set_subtitle("Not installed")
        self.status_session.set_subtitle(d["session"].capitalize())
        self.status_sources.set_subtitle(d["sources"])

        # Switching
        self.switch_shortcut_row.set_subtitle(d["shortcut"])

        # Typing settings
        s = d["settings"]
        self.preview_row.set_active(s.get("switch-preview", True))
        self.newline_row.set_active(s.get("switch-newline", False))
        self.dict_row.set_active(s.get("switch-dict", True))
        self.sug_adj.set_value(s.get("lutable-size", 15))
        self.orient_dropdown.set_selected(s.get("cboxorient", 0))
        self._on_preview_changed(self.preview_row, None)

        # Fixes
        ok = lambda v: "Applied" if v else "Not applied"
        self.fix_shift.set_subtitle(ok(d["shift_fix"]))
        self.fix_debug.set_subtitle(ok(d["debug_off"]))
        self.fix_gtk4.set_subtitle(ok(d["gtk4_prefs"]))
        self.fix_wayland.set_subtitle(ok(d["wayland"]))
        self.fix_apt.set_subtitle(ok(d["apt_hook"]))

        return False


# ============================================================================
# Entry point
# ============================================================================

def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = AvroManagerApp()
    app.run(None)


if __name__ == "__main__":
    main()
