# Changelog

All notable changes to ibus-avro-fixed are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.4.0] - 2026-04-12

### Fixed
- **Bangla typing not working after install/reboot** — on GNOME 50+ / Wayland, `GTK_IM_MODULE=ibus` is not set by the system (GNOME handles IBus natively but doesn't export the env var). GTK apps didn't know to use IBus, so typing stayed in English even though Super+Space switched the indicator. Fix: installer now creates `~/.config/environment.d/10-ibus-avro.conf` with all three IBus env vars (`GTK_IM_MODULE`, `QT_IM_MODULE`, `XMODIFIERS`). Uninstaller cleans it up.

---

## [2.3.0] - 2026-04-12

### Changed
- **README completely rewritten** — removed .deb install section, removed multi-step manual install. Now one command: `git clone + bash install.sh`. Clear focus on the core mission: fix upstream ibus-avro for Wayland/GNOME 50+.
- **Install is truly one command** — git clone, install base + all fixes + GUI + desktop shortcut + auto-launch, all from `bash install.sh`.

---

## [2.2.1] - 2026-04-12

### Changed
- **Single command install** — `install.sh` now includes GUI setup (step 7/7): installs Python GTK4 deps, creates desktop shortcut, and auto-launches the manager. No separate `setup-gui.sh` needed. One command does everything: `git clone` + `bash install.sh`.

---

## [2.2.0] - 2026-04-12

### Added
- **Comprehensive activity logging** — every user action, system command, and result logged to `~/.local/share/avro-manager/avro.log`. Includes GUI events, fix application, pkexec auth, install/uninstall steps, and errors. Auto-rotates at 1MB (3 backups).
- **In-GUI log viewer** — "View Log" button in Diagnostics section opens a scrollable text view with "Copy to clipboard" for easy bug reporting. "Clear Log" for fresh debugging sessions.
- **Self-update from Git** — "Check for Updates" button in Maintenance section. Fetches latest from GitHub, shows what changed, one-click "Update Now" pulls and auto-restarts GUI. No uninstall/reinstall needed.
- **Proper uninstall with progress bar** — step-by-step progress: removing APT hook → restoring upstream → removing autostart → restarting IBus. Handles pkexec cancellation gracefully.
- **Single instance** — `GApplication` prevents duplicate windows when clicking the app icon while already open.
- **Install/uninstall script logging** — `install.sh` and `uninstall.sh` write to the same log file.

### Improved
- **Non-blocking UI** — all operations (configure switching, apply typing settings, restart IBus, uninstall) now run in background threads. UI never freezes.
- **Security** — temp uninstall scripts use `tempfile.mkstemp()` with `0o700` permissions instead of predictable `/tmp/` paths.

---

## [2.1.0] - 2026-04-12

### Added
- **Full GTK4 GUI Manager** (`avro-manager.py`) with:
  - Status panel: iBus daemon, Avro engine, session type, input sources
  - Input switching: configure Super+Space with one click, autostart persistence
  - Typing settings: preview, dictionary, suggestions, orientation — all live
  - Fix status dashboard: Shift fix, debug logging, GTK4 prefs, Wayland, APT hook
  - Maintenance: restart iBus, open preferences, keyboard settings, restore upstream
- `setup-gui.sh` — installs GUI dependencies and creates desktop shortcut
- GUI mentioned in install.sh completion message

---

## [2.0.1] - 2026-04-12

### Fixed
- **CRITICAL: GTK3/GTK4 conflict** — pref.js was imported at module level in main-gjs.js, loading GTK4 into the engine process which could crash if IBus had loaded GTK3. Preferences now launch as a separate process via `GLib.spawn_command_line_async()`.
- **Incomplete debug logging disable** — `print()` on line 151 (orientation) and line 198 (candidate click) were not caught by the sed pattern. All debug prints are now commented out in source. APT hook pattern updated to catch all `print()` calls.

---

## [2.0.0] - 2026-04-12

### Fixed
- **Left Shift key bug** — keycode 42 was consumed by the engine (`return true`), preventing Left Shift from working system-wide when Avro was active. Changed to `return false`.
- **Right Shift key** — keycode 54 also now passes through correctly.
- **Debug keypress logging** — disabled noisy `print()` on every keystroke that spammed the journal.

### Added
- **GTK4/libadwaita preferences window** — replaces outdated GTK3 UI with modern GNOME design using Adw.SwitchRow, Adw.SpinRow, Adw.PreferencesGroup.
- **Wayland input switching** — configures Super+Space / Shift+Super+Space via GNOME gsettings (iBus X11 key grabs don't work on Wayland).
- **APT hook** — automatically re-applies fixes when `apt upgrade` overwrites ibus-avro files.
- **Autostart entry** — input switching shortcuts persist across reboots and dconf resets.
- **One-command installer** (`install.sh`) — handles fresh install or patching existing ibus-avro.
- **.deb package** — `ibus-avro-fixed` replaces upstream `ibus-avro` with all fixes built in.

### Based On
- [sarim/ibus-avro](https://github.com/sarim/ibus-avro) v1.2 (last updated 2023-09-14)
- Licensed under MPL 2.0
