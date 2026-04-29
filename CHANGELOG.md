# Changelog

All notable changes to ibus-avro-fixed are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.5.4] - 2026-04-29

### Changed
- `uninstall.sh` now also removes its own source directory (the cloned `~/ibus-avro-fixed`) as the final step. v2.5.3 left the repo in place, which meant the README's `git clone … ~/ibus-avro-fixed && bash install.sh` re-test failed with `destination path already exists`. "Uninstall like it never existed" means the source tree goes too.

---

## [2.5.3] - 2026-04-29

### Changed
- **`uninstall.sh` now does total purge by default** (breaking change in semantics, not in API). Previous behaviour: removed our fixes and restored stock upstream `ibus-avro` — useful for "back to vanilla" but useless for repeated install/uninstall test cycles, since each run left the IBus tray icon, the registered engine, and all base packages in place. New behaviour: purges every IBus apt package (`ibus`, `ibus-avro`, `ibus-data`, `ibus-gtk3`, `ibus-gtk4`), autoremoves orphans, kills leftover daemon/helper processes, wipes user state (`~/.config/ibus`, `~/.local/share/avro-manager`, autostart, `environment.d/10-ibus-avro.conf`), unbinds the KDE kglobalaccel Meta+Space action, and removes the toggle script and APT hook. End state: `which ibus` not found, no tray icon, system identical to pre-install. A `bash uninstall.sh && bash install.sh` cycle is now a true smoke test.

### Added
- README "Uninstall" section now distinguishes the two paths: `bash uninstall.sh` = total purge (recommended); GUI "Restore Upstream" button = remove our fixes but keep stock IBus installed.

---

## [2.5.2] - 2026-04-29

### Fixed
- **Super+Space did not actually work on KDE Plasma 6 Wayland in v2.5.0** — the IBus hotkey trigger (`org.freedesktop.ibus.general.hotkey trigger`) is X11-era (relies on X keygrabs) and is decorative on Wayland. v2.5.0's KDE branch set it but the daemon couldn't enforce it, so users had to log out/in or fall back to the IBus tray menu. **Fix:** new `ibus-avro-toggle.sh` (installed to `/usr/local/bin/ibus-avro-toggle`) plus a user `.desktop` file, registered live with `org.kde.KGlobalAccel.setShortcut` via DBus. Binding takes effect immediately, persists across logins via `~/.config/kglobalshortcutsrc`.
- **IBus startup notification "unset QT_IM_MODULE / GTK_IM_MODULE"** — v2.4.0 added `~/.config/environment.d/10-ibus-avro.conf` setting those vars, which is correct for GNOME 50+ Wayland (GNOME doesn't auto-export them) but wrong for KDE Plasma 6 Wayland (`text-input-v3` handles IM natively, the vars are redundant and trigger the warning). Now branched: GNOME/other write the env file, KDE skips it (and removes any stale copy from a prior install on the same machine).
- **IBus startup notification "ibus-daemon should be executed as a child process of ibus-ui-gtk3"** — `ibus restart` (step 6 of `install.sh`) re-launched the daemon directly, so its parent was the install shell instead of `ibus-ui-gtk3 --enable-wayland-im --exec-daemon`. Replaced with `systemctl --user restart org.freedesktop.IBus.session.GNOME.service` (the universal user unit shipped by IBus, used by Kubuntu / Pop / Mint too despite the name). Falls back to `ibus restart` if the unit isn't present.

### Added
- `ibus-avro-toggle.sh` (new repo file) — two-engine toggle (`ibus-avro` ↔ `xkb:us::eng`), invoked by KDE's kglobalaccel binding.
- README "After install" section now covers the right-click → IBus tray → Preferences → Input Method → Bangla → Avro Phonetic flow as the canonical first-time setup.
- Troubleshooting note about Kubuntu 26.04's `plasma-kglobalaccel5.service` packaging bug (both Plasma 5 and Plasma 6 unit files ship in the package, conflicting on the same DBus name; mask the .5 one).

### Changed
- `setup-wayland.sh` KDE branch no longer sets the IBus trigger; it now writes `~/.local/share/applications/com.github.mmhfarooque.ibus-avro-toggle.desktop` and DBus-registers Meta+Space.
- `avro-manager.py`: `is_wayland_switching_configured()` and `get_switch_shortcut()` now query `org.kde.kglobalaccel` on KDE instead of the (broken-on-Wayland) IBus trigger gsetting.
- `uninstall.sh`: removes the new toggle script (`/usr/local/bin/ibus-avro-toggle`), the desktop file, and unbinds the kglobalaccel action.

---

## [2.5.0] - 2026-04-29

### Added
- **KDE Plasma 6 support** — single install now works on both GNOME and KDE Plasma 6 Wayland. `setup-wayland.sh` and the GUI auto-detect `XDG_CURRENT_DESKTOP` and choose the right switching backend:
  - **GNOME:** sets `org.gnome.desktop.wm.keybindings switch-input-source` (Mutter intercepts the shortcut), clears IBus trigger to avoid conflicts.
  - **KDE / other:** sets `org.freedesktop.ibus.general.hotkey trigger` to `['<Super>space']` (IBus owns the hotkey, since KWin does not intercept Super+Space by default on Plasma 6).
- `detect_de()` helper in `avro-manager.py`; six callsites branched off it (input-source reader, switching-configured check, shortcut display, "Configure" button, "Open Keyboard Settings" button).
- README: new "Why two different switching strategies?" section explaining the per-DE behaviour.

### Fixed
- **Autostart `.desktop` rejected by systemd-xdg-autostart-generator on every boot** with `Undefined escape sequence \"`. The previous `Exec=bash -c "...\"['<Super>space']\"..."` violated the desktop-entry spec; the entry was silently dropped, so dconf resets between sessions weren't being re-applied. Replaced with a normal `Exec=/path/to/setup-wayland.sh` and a real script — no inline bash escapes.
- **`get_current_input_sources()`** was reading `org.gnome.desktop.input-sources sources`, which doesn't exist on KDE. Now reads `org.freedesktop.ibus.general preload-engines` (universal across DEs).

### Changed
- "Open GNOME Keyboard Settings" maintenance row → "Open Keyboard Settings"; on KDE it launches `systemsettings kcm_keyboard` (with `kcmshell6/5` fallbacks).

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
