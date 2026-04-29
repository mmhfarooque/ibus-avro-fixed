# ibus-avro-fixed — Avro Phonetic Bangla for Linux (Left Shift Fix + Wayland + GNOME / KDE)

Avro Phonetic lets you type Bangla by writing English phonetically — it transliterates as you type. This is a **fixed fork** of [ibus-avro](https://github.com/sarim/ibus-avro) that solves all known bugs including the **Left Shift key bug** and **Wayland input switching** on modern Ubuntu (GNOME) and Kubuntu (KDE Plasma).

The upstream `ibus-avro` was built for X11/Xorg and has been unmaintained since 2023. It has critical bugs on Ubuntu 24.04+ and Wayland. This project fixes everything and includes a modern GTK4 GUI manager that auto-detects your desktop and configures input switching the right way for it.

![IBus Avro Manager](screenshot.png)

---

## Install (One Command)

```bash
git clone https://github.com/mmhfarooque/ibus-avro-fixed.git ~/ibus-avro-fixed && cd ~/ibus-avro-fixed && bash install.sh
```

That's it. The installer handles everything:
- Installs `ibus-avro` from Ubuntu repos (if needed)
- Applies Left Shift + Right Shift fix
- Disables debug keypress logging
- Installs GTK4 preferences window
- Sets up APT hook (fixes survive system updates)
- Configures Super+Space switching for Wayland
- Installs GUI Manager + desktop shortcut
- Auto-launches the GUI

### After install

> ### ⚠️ Log out and log back in (one-time)
>
> The installer does everything that *can* be done from a script, but the desktop session's input-method service only attaches at session start. Log out and log back in once after `install.sh` finishes. After that, Super+Space switching, Bangla typing, and the IBus tray icon all work normally.
>
> Symptoms if you skip this step (especially on KDE Plasma 6 Wayland):
> - Bangla typing stays English in some apps
> - Super+Space doesn't switch
> - "IBus should be called from the desktop session in Wayland" notification keeps appearing
>
> A full reboot also works. Once is enough — subsequent `install.sh` re-runs (e.g. to apply a new release) do not require another logout.

**One-time setup — register Avro with IBus** (after the logout/login):

1. Right-click the **IBus tray icon** → **Preferences**
2. Open the **Input Method** tab → click **Add**
3. Expand **Bangla** → select **Avro Phonetic** → **OK**

(On GNOME you can also use **Settings → Keyboard → Input Sources → Add**. KDE has a similar path under System Settings, but the IBus tray menu is the canonical one.)

**Then start typing:**

1. Press **Super+Space** to switch between English and Bangla
2. Type `ami bangla likhte pari` → আমি বাংলা লিখতে পারি

Super+Space is bound at the desktop level: GNOME via Mutter (`org.gnome.desktop.wm.keybindings`), KDE Plasma 6 via kglobalaccel + a toggle script. Both DEs route the hotkey without IBus's broken-on-Wayland keygrab.

---

## What's Fixed

| Bug | Severity | Upstream (X11 era) | This Fork |
|-----|----------|---------------------|-----------|
| Left Shift key broken | **Critical** | Consumes keycode 42 | Passes through |
| Right Shift key broken | **Critical** | Not handled | Passes through |
| Input switching on Wayland | **Medium** | X11 key grabs, broken | DE-aware (GNOME WM keybinding / IBus trigger on KDE) |
| Preferences window | **Medium** | GTK3, broken on GNOME 42+ | GTK4 + libadwaita |
| Updates break fixes | **Low** | No solution | APT hook auto-fixes |
| Debug log spam | **Low** | Every keypress logged | Disabled |

### Why two different switching strategies?

- **GNOME (Mutter/Wayland):** the compositor intercepts global shortcuts before applications see them, so IBus's own hotkey can't fire. We set `org.gnome.desktop.wm.keybindings switch-input-source` to `<Super>space` — Mutter handles it.
- **KDE Plasma 6+ (KWin/Wayland):** IBus's own `org.freedesktop.ibus.general.hotkey trigger` schema is X11-era (relies on X keygrabs) and is decorative on Wayland. We bind `Meta+Space` at the KDE level via `kglobalaccel` → `/usr/local/bin/ibus-avro-toggle`, registered live through DBus (`org.kde.KGlobalAccel.setShortcut`). Works in-session — no logout required.

`setup-wayland.sh` auto-detects the desktop via `XDG_CURRENT_DESKTOP` and runs the right path. The GUI's "Configure Super+Space" button just calls the same script.

### Why these bugs exist

The original ibus-avro was built for **X11/Xorg** in 2012. Ubuntu switched to **Wayland** as default in 2021 (Ubuntu 21.10). The Left Shift bug has existed for **14 years** — `return true` for keycode 42 tells IBus "I consumed this key" so the OS never sees it.

---

## GUI Manager

The IBus Avro Manager is a full GTK4/libadwaita application. Search **"Avro"** in your app launcher.

**Features:**
- **Status** — IBus daemon, Avro engine, session type (Wayland/X11), input sources
- **Input Switching** — current shortcut, one-click Super+Space configuration
- **Typing Settings** — preview window, dictionary, Enter behaviour, max suggestions
- **Fix Status** — dashboard showing which fixes are applied, "Apply All Fixes" button
- **Maintenance** — restart IBus, open preferences, open GNOME keyboard settings
- **Check for Updates** — self-update from Git without reinstalling
- **Restore Upstream** — uninstall all fixes with progress bar
- **Diagnostics** — activity log viewer with copy-to-clipboard for bug reporting

---

## Updates

The GUI has a **"Check for Updates"** button. It fetches the latest from GitHub, shows what changed, and updates with one click. The GUI auto-restarts after updating. No need to uninstall or re-clone.

---

## Uninstall

From terminal — **total purge** (default, since v2.5.3):

```bash
cd ~/ibus-avro-fixed && bash uninstall.sh
```

This removes **everything** the project ever touched: all IBus apt packages (`ibus`, `ibus-avro`, `ibus-data`, `ibus-gtk3`, `ibus-gtk4`) plus orphans, the APT hook, the toggle script, all user state (`~/.config/ibus`, `~/.local/share/avro-manager`, autostart, `environment.d/10-ibus-avro.conf`), KDE's kglobalaccel Meta+Space binding, and any running IBus processes. After it finishes, `which ibus` returns nothing and the tray icon is gone — system is in the same state as before you ever installed.

This makes a fresh `bash install.sh` smoke test a one-liner: `bash uninstall.sh && bash install.sh`.

From the GUI: scroll to Maintenance → click **"Restore Upstream"**. (This is **not** the same as `uninstall.sh` — it removes our patches but keeps stock `ibus-avro` installed and registered, so you go back to the upstream broken-Shift state. Use it if you want to keep IBus running but drop our customisations.)

---

## Supported Systems

**Verified working** (smoke-tested end-to-end on v2.5.x):
- **Kubuntu 26.04 LTS — KDE Plasma 6.6.4 Wayland**

**Code path preserved from v2.4.0 (which was working) — re-verification for v2.5.x pending**:
- **Ubuntu 26.04 LTS — GNOME 50+ Wayland**

A single install supports both GNOME and KDE. The installer detects `XDG_CURRENT_DESKTOP` and configures Super+Space switching the right way for your desktop.

**Not supported** in the current installer:
- Fedora, Arch, openSUSE — `install.sh` uses `apt`/`dpkg` and the APT hook lives in `/etc/apt/apt.conf.d/`. The patches themselves (the keycode 42 fix, GTK4 prefs, kglobalaccel binding) are distro-agnostic and could be ported, but the install scripts haven't been written or tested for `dnf` / `pacman` / `zypper`. Pull requests welcome.
- Debian, Linux Mint, Pop!_OS, KDE Neon, older Ubuntu/Kubuntu — same Debian-based code path so they *should* work, but I haven't tested any of them on the v2.5.x line. Try at your own risk; file an issue if anything breaks.

---

## How Avro Phonetic Works

Type English letters and Avro converts them to Bangla phonetically:

| You type | You get |
|----------|---------|
| `ami` | আমি |
| `bangla` | বাংলা |
| `bhalo` | ভালো |
| `dhaka` | ঢাকা |
| `tumi kemon acho` | তুমি কেমন আছো |
| `amar sonar bangla` | আমার সোনার বাংলা |

Full phonetic rules: [Avro Phonetic Layout](https://avro.im/layout)

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Super+Space doesn't switch | Open GUI Manager → "Configure Super+Space Switching" |
| Super+Space conflicts with KRunner / KWin shortcut on KDE | Open System Settings → Shortcuts → Global Shortcuts and unbind anything on `Meta+Space` |
| Left Shift still broken | Open GUI Manager → "Apply All Fixes" |
| Avro not in input source list | Run `ibus restart`, then add in your DE's Keyboard settings |
| Fixes disappear after update | APT hook should handle this. If not, run `bash install.sh` again |
| Nothing works after reboot | Log out and log back in (IBus starts on login) |
| `ibus-ui-gtk3: Window is a temporary window without parent` warnings on KDE | Harmless. Upstream IBus indicator quirk under KWin/Wayland — not from this project. |
| IBus notification: "unset QT_IM_MODULE / GTK_IM_MODULE / ibus-daemon should be a child of ibus-ui-gtk3" | v2.5.2+ install avoids this on KDE (skips the env file, restarts via the systemd user unit so the daemon is properly parented). If you saw it after a v2.5.0/2.5.1 install, re-run `bash install.sh`. |
| Spectacle screenshot fails with "Did not receive a reply" on Kubuntu 26.04 | Known Kubuntu 26.04 packaging bug — both `plasma-kglobalaccel.service` and `plasma-kglobalaccel5.service` ship together, conflicting on the same DBus name. Workaround: `systemctl --user mask plasma-kglobalaccel5.service`. |

For detailed debugging, open the GUI Manager → **Diagnostics → View Log** → copy and paste.

---

## Credits

- **Original:** [Sarim Khan](https://github.com/sarim/ibus-avro) — ibus-avro engine and phonetic library
- **Contributors:** Mehdi Hasan Khan (dictionary support)
- **Fixes, GTK4 port, GUI Manager:** [Mahmud Farooque](https://github.com/mmhfarooque)

## License

MPL 2.0 (same as upstream ibus-avro)
