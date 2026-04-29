#!/usr/bin/env python3
"""
IBus Avro Manager — Full GUI for ibus-avro-fixed.

Fixes upstream ibus-avro for Wayland on GNOME 50+ and KDE Plasma 6+:
  - Left Shift key fix (keycode 42 was consumed by the engine)
  - Right Shift key fix (keycode 54)
  - Super+Space input switching (X11 key grabs don't work on Wayland)
  - GTK4/libadwaita preferences (replaces broken GTK3 prefs)
  - APT hook for persistence across system updates

Uses GTK4 + libadwaita; runs on GNOME, KDE Plasma, and other DEs.
"""

import gi
import logging
import logging.handlers
import os
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import threading
import time

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk

APP_ID = "com.github.mmhfarooque.avro-manager"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INSTALL_DIR = "/usr/share/ibus-avro"
MAIN_GJS = os.path.join(INSTALL_DIR, "main-gjs.js")

# ============================================================================
# Logging — all events to ~/.local/share/avro-manager/avro.log
# ============================================================================

LOG_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "avro-manager")
LOG_FILE = os.path.join(LOG_DIR, "avro.log")
os.makedirs(LOG_DIR, exist_ok=True)

log = logging.getLogger("avro")
log.setLevel(logging.DEBUG)

_fh = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3)
_fh.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
))
log.addHandler(_fh)

_sh = logging.StreamHandler()
_sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
_sh.setLevel(logging.INFO)
log.addHandler(_sh)

# ============================================================================
# Version
# ============================================================================

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
    """Run a command and return (returncode, stdout, stderr)."""
    cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
    log.debug(f"CMD: {cmd_str} (timeout={timeout}s)")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            log.warning(f"CMD FAILED (rc={r.returncode}): {cmd_str} | stdout={r.stdout.strip()[:200]!r} | stderr={r.stderr.strip()[:200]!r}")
        else:
            log.debug(f"CMD OK: {cmd_str}")
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        log.error(f"CMD TIMEOUT ({timeout}s): {cmd_str}")
        return 1, "", f"Command timed out after {timeout}s"
    except FileNotFoundError:
        log.error(f"CMD NOT FOUND: {cmd_str}")
        return 1, "", f"Command not found: {cmd[0]}"


def run_as_root(cmd_str):
    """Run a shell command as root via pkexec."""
    log.info(f"ROOT CMD: {cmd_str}")
    return run_cmd(["pkexec", "bash", "-c", cmd_str], timeout=120)


def is_ibus_running():
    rc, _, _ = run_cmd(["pgrep", "-x", "ibus-daemon"])
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


def detect_de():
    """Return 'gnome', 'kde', or 'other' from XDG_CURRENT_DESKTOP."""
    de = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
    if "GNOME" in de:
        return "gnome"
    if "KDE" in de:
        return "kde"
    return "other"


def get_current_input_sources():
    # IBus's preload-engines schema works on every DE; GNOME's
    # org.gnome.desktop.input-sources only exists on GNOME.
    rc, out, _ = run_cmd([
        "gsettings", "get", "org.freedesktop.ibus.general", "preload-engines"
    ])
    return out if rc == 0 else "Unknown"


def is_shift_fix_applied():
    """Check if Left Shift bug is fixed."""
    try:
        with open(MAIN_GJS) as f:
            content = f.read()
            if "keycode == 42" not in content:
                return False
            after = content.split("keycode == 42")[1][:200]
            return "return false" in after and "return true" not in after
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
    # GNOME: WM owns the shortcut (gnome.desktop.wm.keybindings).
    # KDE:   kglobalaccel owns it; we registered it under our .desktop file.
    # Other: best-effort IBus trigger.
    de = detect_de()
    if de == "gnome":
        rc, out, _ = run_cmd([
            "gsettings", "get", "org.gnome.desktop.wm.keybindings", "switch-input-source"
        ])
        return "<Super>space" in out if rc == 0 else False
    if de == "kde":
        # Ask kglobalaccel directly via gdbus — survives even if the
        # kglobalshortcutsrc file hasn't been flushed yet.
        action_id = ("['com.github.mmhfarooque.ibus-avro-toggle.desktop',"
                     "'_launch','Toggle Avro/English Input',"
                     "'Toggle Avro/English Input']")
        rc, out, _ = run_cmd([
            "gdbus", "call", "--session", "--dest", "org.kde.kglobalaccel",
            "--object-path", "/kglobalaccel",
            "--method", "org.kde.KGlobalAccel.shortcut", action_id,
        ])
        # Meta+Space = 268435488; presence of any non-zero binding = configured
        return rc == 0 and "268435488" in out
    rc, out, _ = run_cmd([
        "gsettings", "get", "org.freedesktop.ibus.general.hotkey", "trigger"
    ])
    return "<Super>space" in out if rc == 0 else False


def is_gtk4_prefs_installed():
    pref_path = os.path.join(INSTALL_DIR, "pref.js")
    try:
        with open(pref_path) as f:
            content = f.read()
            return "Adw" in content and "4.0" in content
    except FileNotFoundError:
        return False


def get_avro_settings():
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
    de = detect_de()
    if de == "kde":
        # On KDE the binding lives in kglobalaccel; if our action is bound,
        # report Meta+Space directly.
        return "Meta + Space" if is_wayland_switching_configured() else "Not set"
    if de == "gnome":
        schema, key = "org.gnome.desktop.wm.keybindings", "switch-input-source"
    else:
        schema, key = "org.freedesktop.ibus.general.hotkey", "trigger"
    rc, out, _ = run_cmd(["gsettings", "get", schema, key])
    if rc == 0 and out:
        match = re.search(r"'([^']+)'", out)
        shortcut = match.group(1) if match else out
        return shortcut.replace("<", "Super + ").replace(">", "")
    return "Not set"


# ============================================================================
# Main Application
# ============================================================================


class AvroManagerApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self.on_activate)
        self.win = None

    def on_activate(self, app):
        if self.win is not None:
            log.info("Window already open — bringing to front")
            self.win.present()
            return
        log.info(f"=== IBus Avro Manager v{APP_VERSION} starting ===")
        log.info(f"User: {os.environ.get('USER', 'unknown')} | PID: {os.getpid()}")
        log.info(f"Session: {get_session_type()} | Script dir: {SCRIPT_DIR}")
        log.info(f"Log file: {LOG_FILE}")
        self.win = AvroManagerWindow(application=app)
        self.win.present()


class AvroManagerWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title(f"IBus Avro Manager v{APP_VERSION}")
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
            title="Switch Shortcut", subtitle="Checking...",
        )
        self.switch_shortcut_row.add_prefix(Gtk.Image.new_from_icon_name("input-keyboard-symbolic"))
        group.add(self.switch_shortcut_row)

        self.switch_back_row = Adw.ActionRow(
            title="Switch Back", subtitle="Shift + Super + Space",
        )
        self.switch_back_row.add_prefix(Gtk.Image.new_from_icon_name("go-previous-symbolic"))
        group.add(self.switch_back_row)

        apply_row = Adw.ActionRow(title="")
        self.wayland_btn = Gtk.Button(
            label="Configure Super+Space Switching",
            css_classes=["suggested-action"], valign=Gtk.Align.CENTER,
        )
        self.wayland_btn.connect("clicked", self.on_configure_switching)
        apply_row.add_suffix(self.wayland_btn)
        group.add(apply_row)

    def on_configure_switching(self, btn):
        de = detect_de()
        log.info(f"User: Configure Super+Space switching (DE: {de})")
        btn.set_sensitive(False)

        def do_configure():
            # setup-wayland.sh handles all DE branching and writes the
            # autostart entry. Single source of truth for the shortcut logic.
            script = os.path.join(SCRIPT_DIR, "setup-wayland.sh")
            rc, out, err = run_cmd(["bash", script], timeout=15)
            if rc != 0:
                log.warning(f"setup-wayland.sh failed: rc={rc} stderr={err[:200]!r}")
            else:
                log.info("Super+Space switching configured")

            def _done():
                btn.set_sensitive(True)
                self.show_toast("Super+Space switching configured")
                self.refresh_switching()
                return False
            GLib.idle_add(_done)

        threading.Thread(target=do_configure, daemon=True).start()

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

        self.preview_row = Adw.SwitchRow(
            title="Preview Window",
            subtitle="Show suggestion preview while typing",
        )
        self.preview_row.connect("notify::active", self._on_preview_changed)
        group.add(self.preview_row)

        self.newline_row = Adw.SwitchRow(
            title="Enter Closes Preview Only",
            subtitle="Enter commits text without inserting a new line",
        )
        group.add(self.newline_row)

        self.dict_row = Adw.SwitchRow(
            title="Dictionary Suggestions",
            subtitle="Show Bangla word suggestions from dictionary",
        )
        group.add(self.dict_row)

        self.sug_adj = Gtk.Adjustment(value=15, lower=5, upper=15, step_increment=1)
        self.sug_row = Adw.SpinRow(
            title="Max Suggestions",
            subtitle="Maximum dictionary suggestions (5-15)",
            adjustment=self.sug_adj,
        )
        group.add(self.sug_row)

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
        log.info("User: Apply typing settings")
        btn.set_sensitive(False)

        def do_apply():
            set_avro_setting("switch-preview", self.preview_row.get_active())
            set_avro_setting("switch-newline", self.newline_row.get_active())
            set_avro_setting("switch-dict", self.dict_row.get_active())
            set_avro_setting("lutable-size", int(self.sug_adj.get_value()))
            set_avro_setting("cboxorient", self.orient_dropdown.get_selected())

            def _done():
                btn.set_sensitive(True)
                self.show_toast("Typing settings applied")
                return False
            GLib.idle_add(_done)

        threading.Thread(target=do_apply, daemon=True).start()

    # ========================================================================
    # Fixes Status Section
    # ========================================================================

    def build_fixes_section(self, parent):
        group = Adw.PreferencesGroup(
            title="Fix Status",
            description="Status of all applied bug fixes for Wayland (GNOME / KDE Plasma)",
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

        fix_row = Adw.ActionRow(title="")
        self.apply_all_btn = Gtk.Button(
            label="Apply All Fixes", css_classes=["suggested-action"],
            valign=Gtk.Align.CENTER,
        )
        self.apply_all_btn.connect("clicked", self.on_apply_all_fixes)
        fix_row.add_suffix(self.apply_all_btn)
        group.add(fix_row)

    def on_apply_all_fixes(self, btn):
        log.info("User: Apply all fixes")
        btn.set_sensitive(False)
        btn.set_label("Applying...")
        self.show_toast("Applying all fixes...")

        def do_apply():
            script = os.path.join(SCRIPT_DIR, "install.sh")
            rc, out, err = run_cmd(["bash", script], timeout=120)
            log.info(f"Apply all fixes result: rc={rc}")
            GLib.idle_add(self._apply_done, rc == 0, err)

        threading.Thread(target=do_apply, daemon=True).start()

    def _apply_done(self, success, err):
        self.apply_all_btn.set_sensitive(True)
        self.apply_all_btn.set_label("Apply All Fixes")
        if success:
            self.show_toast("All fixes applied!")
            log.info("All fixes applied successfully")
        else:
            self.show_toast(f"Some fixes failed: {err[:60]}")
            log.error(f"Apply fixes failed: {err[:200]}")
        self.refresh_all()
        return False

    # ========================================================================
    # Maintenance Section
    # ========================================================================

    def build_maintenance_section(self, parent):
        group = Adw.PreferencesGroup(title="Maintenance")
        parent.append(group)

        # Update checker
        self.update_row = Adw.ActionRow(
            title=f"Version: v{APP_VERSION}",
            subtitle="Click to check for updates",
        )
        self.update_row.add_prefix(Gtk.Image.new_from_icon_name("software-update-available-symbolic"))
        self.check_update_btn = Gtk.Button(label="Check for Updates", valign=Gtk.Align.CENTER)
        self.check_update_btn.connect("clicked", self.on_check_update)
        self.update_row.add_suffix(self.check_update_btn)
        group.add(self.update_row)

        # Restart iBus
        restart_row = Adw.ActionRow(
            title="Restart IBus",
            subtitle="Restart the input method framework",
        )
        restart_row.add_prefix(Gtk.Image.new_from_icon_name("view-refresh-symbolic"))
        self._restart_btn = Gtk.Button(label="Restart", valign=Gtk.Align.CENTER)
        self._restart_btn.connect("clicked", self.on_restart_ibus)
        restart_row.add_suffix(self._restart_btn)
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
            subtitle="Open Keyboard Settings to add Avro Phonetic",
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

        # Uninstall progress (hidden until needed)
        self.uninstall_progress = Gtk.ProgressBar(show_text=True, margin_top=8, margin_bottom=4,
            margin_start=12, margin_end=12)
        self.uninstall_progress.set_fraction(0)
        self.uninstall_progress.set_text("")
        self.uninstall_progress.set_visible(False)
        parent.append(self.uninstall_progress)

        # Diagnostics
        diag_group = Adw.PreferencesGroup(title="Diagnostics",
                                           description=f"Log: {LOG_FILE}")
        parent.append(diag_group)

        log_row = Adw.ActionRow(
            title="Activity Log",
            subtitle="View all events for troubleshooting",
        )
        log_row.add_prefix(Gtk.Image.new_from_icon_name("document-open-symbolic"))
        log_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4,
                              valign=Gtk.Align.CENTER)
        view_log_btn = Gtk.Button(label="View Log")
        view_log_btn.connect("clicked", self.on_view_log)
        log_btn_box.append(view_log_btn)
        clear_log_btn = Gtk.Button(label="Clear Log", css_classes=["destructive-action"])
        clear_log_btn.connect("clicked", self.on_clear_log)
        log_btn_box.append(clear_log_btn)
        log_row.add_suffix(log_btn_box)
        diag_group.add(log_row)

    # ========================================================================
    # Update from Git
    # ========================================================================

    def on_check_update(self, btn):
        log.info("User: Check for updates")
        btn.set_sensitive(False)
        btn.set_label("Checking...")
        self.update_row.set_subtitle("Checking for updates...")

        def do_check():
            if not os.path.isdir(os.path.join(SCRIPT_DIR, ".git")):
                GLib.idle_add(self._update_check_done, None, "Not a git clone — updates not available")
                return

            rc, _, err = run_cmd(["git", "-C", SCRIPT_DIR, "fetch", "origin"], timeout=30)
            if rc != 0:
                GLib.idle_add(self._update_check_done, None, f"Fetch failed: {err[:60]}")
                return

            rc, remote_version, _ = run_cmd(
                ["git", "-C", SCRIPT_DIR, "show", "origin/main:VERSION"], timeout=5
            )
            remote_version = remote_version.strip() if rc == 0 else None

            rc, changelog, _ = run_cmd(
                ["git", "-C", SCRIPT_DIR, "log", "HEAD..origin/main",
                 "--oneline", "--no-decorate"], timeout=5
            )

            GLib.idle_add(self._update_check_done, remote_version, changelog)

        threading.Thread(target=do_check, daemon=True).start()

    def _update_check_done(self, remote_version, changelog):
        self.check_update_btn.set_sensitive(True)
        self.check_update_btn.set_label("Check for Updates")

        if remote_version is None:
            self.update_row.set_subtitle(f"v{APP_VERSION} — could not check remote")
            self.show_toast(f"Update check failed: {changelog}")
            return False

        if not changelog or remote_version == APP_VERSION:
            self.update_row.set_subtitle(f"v{APP_VERSION} — up to date!")
            log.info(f"No updates (local={APP_VERSION}, remote={remote_version})")
            self.show_toast("You're on the latest version!")
            return False

        log.info(f"Update available: v{APP_VERSION} → v{remote_version}")
        self.update_row.set_subtitle(f"v{APP_VERSION} → v{remote_version} available")

        dialog = Adw.AlertDialog(
            heading=f"Update available: v{remote_version}",
            body=f"You have v{APP_VERSION}. Changes:\n\n{changelog}\n\n"
                 "The GUI will restart after updating.",
        )
        dialog.add_response("cancel", "Later")
        dialog.add_response("update", "Update Now")
        dialog.set_response_appearance("update", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_update_confirmed, remote_version)
        dialog.present(self)
        return False

    def _on_update_confirmed(self, dialog, response, remote_version):
        log.info(f"Update dialog response: {response}")
        if response != "update":
            return

        self.check_update_btn.set_sensitive(False)
        self.update_row.set_subtitle("Updating...")

        def do_update():
            rc, out, err = run_cmd(["git", "-C", SCRIPT_DIR, "pull", "origin", "main"], timeout=60)
            if rc != 0:
                log.error(f"git pull failed: {err}")
                GLib.idle_add(self._update_failed, err)
                return

            log.info("Update pulled successfully")

            def _restart():
                self.update_row.set_subtitle(f"Updated to v{remote_version} — restarting...")
                self.show_toast("Updated! Restarting GUI...")
                GLib.timeout_add(1500, self._restart_gui)
                return False
            GLib.idle_add(_restart)

        threading.Thread(target=do_update, daemon=True).start()

    def _update_failed(self, err):
        self.check_update_btn.set_sensitive(True)
        self.check_update_btn.set_label("Check for Updates")
        self.update_row.set_subtitle(f"v{APP_VERSION} — update failed")
        self.show_toast(f"Update failed: {err[:60]}")
        return False

    def _restart_gui(self):
        log.info("=== GUI restarting after update ===")
        subprocess.Popen([sys.executable, os.path.join(SCRIPT_DIR, "avro-manager.py")])
        self.close()
        return False

    # ========================================================================
    # Restart IBus / Preferences / Settings
    # ========================================================================

    def on_restart_ibus(self, btn):
        log.info("User: Restart IBus")
        btn.set_sensitive(False)

        def do_restart():
            run_cmd(["ibus", "restart"])
            time.sleep(2)
            def _done():
                btn.set_sensitive(True)
                self.show_toast("IBus restarted")
                self.refresh_all()
                return False
            GLib.idle_add(_done)

        threading.Thread(target=do_restart, daemon=True).start()

    def on_open_prefs(self, btn):
        log.info("User: Open Avro preferences")
        pref_js = os.path.join(INSTALL_DIR, "pref.js")
        if os.path.exists(pref_js):
            subprocess.Popen([
                "/usr/bin/env", "gjs",
                f"--include-path={INSTALL_DIR}", pref_js, "--standalone"
            ])
            self.show_toast("Preferences window opened")
        else:
            self.show_toast("pref.js not found — run Apply All Fixes first")

    def on_open_keyboard_settings(self, btn):
        de = detect_de()
        log.info(f"User: Open Keyboard Settings (DE: {de})")
        candidates = {
            "gnome": [["gnome-control-center", "keyboard"]],
            "kde":   [["systemsettings", "kcm_keyboard"],
                      ["kcmshell6", "kcm_keyboard"],
                      ["kcmshell5", "kcm_keyboard"]],
        }.get(de, [["xdg-open", "settings://"]])

        for cmd in candidates:
            try:
                subprocess.Popen(cmd)
                return
            except FileNotFoundError:
                continue
        self.show_toast("No keyboard settings command found for this desktop")

    # ========================================================================
    # Uninstall (Restore Upstream)
    # ========================================================================

    def on_uninstall(self, btn):
        log.info("User: clicked Restore Upstream")
        dialog = Adw.AlertDialog(
            heading="Restore upstream ibus-avro?",
            body="This removes all fixes:\n\n"
                 "- Left/Right Shift fix\n"
                 "- GTK4 preferences\n"
                 "- Wayland Super+Space switching\n"
                 "- APT hook (persistence)\n\n"
                 "The Left Shift bug will come back.",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("restore", "Restore Upstream")
        dialog.set_response_appearance("restore", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_uninstall_confirmed)
        dialog.present(self)

    def _on_uninstall_confirmed(self, dialog, response):
        log.info(f"Uninstall dialog response: {response}")
        if response != "restore":
            return

        log.info("=== UNINSTALL STARTING ===")
        self.uninstall_progress.set_visible(True)
        self.uninstall_progress.set_fraction(0)
        self.uninstall_progress.set_text("Starting...")

        def do_uninstall():
            def _update(fraction, text):
                self.uninstall_progress.set_fraction(fraction)
                self.uninstall_progress.set_text(text)
                return False

            # Step 1-2: Remove APT hook + restore upstream (combined in pkexec)
            GLib.idle_add(_update, 0.1, "Step 1/4 — Removing APT hook...")
            log.info("Uninstall step 1: creating temp script for pkexec")

            fd, tmp_script = tempfile.mkstemp(prefix="avro-uninstall-", suffix=".sh")
            try:
                with os.fdopen(fd, "w") as f:
                    f.write("#!/bin/bash\n")
                    f.write("rm -f /etc/apt/apt.conf.d/99-fix-ibus-avro\n")
                    f.write("rm -f /usr/local/bin/fix-ibus-avro.sh\n")
                    f.write("apt install --reinstall -y ibus-avro 2>/dev/null || true\n")
                os.chmod(tmp_script, 0o700)

                GLib.idle_add(_update, 0.3, "Step 2/4 — Restoring upstream (enter password)...")
                log.info("Uninstall step 2: running pkexec (password prompt expected)")
                rc, out, err = run_cmd(["pkexec", tmp_script], timeout=120)
            finally:
                try:
                    os.remove(tmp_script)
                except FileNotFoundError:
                    pass

            log.info(f"Uninstall pkexec result: rc={rc}")
            if rc != 0:
                log.warning("Uninstall aborted — pkexec cancelled or failed")
                def _aborted():
                    self.uninstall_progress.set_fraction(0)
                    self.uninstall_progress.set_text("Uninstall cancelled")
                    self.show_toast("Uninstall cancelled")
                    return False
                GLib.idle_add(_aborted)
                return

            # Step 3: Remove autostart + desktop shortcut
            GLib.idle_add(_update, 0.7, "Step 3/4 — Removing autostart entry...")
            log.info("Uninstall step 3: removing autostart + shortcut")
            for f in [
                os.path.expanduser("~/.config/autostart/ibus-avro-wayland-fix.desktop"),
                os.path.expanduser("~/.local/share/applications/avro-manager.desktop"),
                os.path.expanduser("~/.config/environment.d/10-ibus-avro.conf"),
            ]:
                try:
                    os.remove(f)
                except FileNotFoundError:
                    pass

            # Step 4: Restart ibus
            GLib.idle_add(_update, 0.9, "Step 4/4 — Restarting IBus...")
            log.info("Uninstall step 4: restarting ibus")
            run_cmd(["ibus", "restart"])
            time.sleep(1)

            log.info("=== UNINSTALL COMPLETE ===")
            def _done():
                self.uninstall_progress.set_fraction(1.0)
                self.uninstall_progress.set_text("Upstream restored — fixes removed")
                self.show_toast("Upstream ibus-avro restored")
                self.refresh_all()
                return False
            GLib.idle_add(_done)

        threading.Thread(target=do_uninstall, daemon=True).start()

    # ========================================================================
    # Log Viewer
    # ========================================================================

    def on_view_log(self, btn):
        log.info("User opened log viewer")
        try:
            with open(LOG_FILE) as f:
                content = f.read()
        except FileNotFoundError:
            content = "(No log file yet)"

        dialog = Adw.Dialog()
        dialog.set_title("Activity Log")
        dialog.set_content_width(750)
        dialog.set_content_height(500)

        toolbar_view = Adw.ToolbarView()
        dialog.set_child(toolbar_view)

        header = Adw.HeaderBar()
        copy_btn = Gtk.Button(icon_name="edit-copy-symbolic", tooltip_text="Copy log to clipboard")
        header.pack_end(copy_btn)
        toolbar_view.add_top_bar(header)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        text_view = Gtk.TextView(editable=False, monospace=True,
                                  wrap_mode=Gtk.WrapMode.WORD_CHAR,
                                  top_margin=8, bottom_margin=8,
                                  left_margin=8, right_margin=8)
        text_view.get_buffer().set_text(content)
        scroll.set_child(text_view)
        toolbar_view.set_content(scroll)

        def _scroll_to_end(*args):
            adj = scroll.get_vadjustment()
            adj.set_value(adj.get_upper())
            return False
        GLib.idle_add(_scroll_to_end)

        def _copy(*args):
            clipboard = self.get_clipboard()
            clipboard.set(content)
            self.show_toast("Log copied to clipboard")
        copy_btn.connect("clicked", _copy)

        dialog.present(self)

    def on_clear_log(self, btn):
        log.info("User cleared log")
        for handler in log.handlers[:]:
            if isinstance(handler, logging.handlers.RotatingFileHandler):
                handler.close()
                log.removeHandler(handler)
        with open(LOG_FILE, "w") as f:
            f.write("")
        fh = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        ))
        log.addHandler(fh)
        log.info(f"=== Log cleared — IBus Avro Manager v{APP_VERSION} ===")
        self.show_toast("Log cleared")

    # ========================================================================
    # Refresh all
    # ========================================================================

    def refresh_all(self):
        log.debug("Refreshing all status...")

        def do_refresh():
            try:
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
            except Exception as e:
                log.exception(f"Refresh error: {e}")

        threading.Thread(target=do_refresh, daemon=True).start()

    def _apply_refresh(self, d):
        try:
            return self._do_apply_refresh(d)
        except Exception as e:
            log.exception(f"UI refresh error: {e}")
        return False

    def _do_apply_refresh(self, d):
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
        ok_text = lambda v: "Applied" if v else "Not applied"
        self.fix_shift.set_subtitle(ok_text(d["shift_fix"]))
        self.fix_debug.set_subtitle(ok_text(d["debug_off"]))
        self.fix_gtk4.set_subtitle(ok_text(d["gtk4_prefs"]))
        self.fix_wayland.set_subtitle(ok_text(d["wayland"]))
        self.fix_apt.set_subtitle(ok_text(d["apt_hook"]))

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
