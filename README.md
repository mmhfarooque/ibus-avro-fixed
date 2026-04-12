# ibus-avro-fixed — Avro Phonetic Bangla for Linux (Left Shift Fix + Wayland + GNOME 50)

Avro Phonetic lets you type Bangla by writing English phonetically — it transliterates as you type. This is a **fixed fork** of [ibus-avro](https://github.com/sarim/ibus-avro) that solves all known bugs including the **Left Shift key bug** and **Wayland input switching** on modern Ubuntu/Debian.

The upstream `ibus-avro` has been unmaintained since 2023 and has several critical bugs on Ubuntu 24.04+ and Wayland. This project provides a **complete, working package** with a modern GTK4 GUI manager — install it and everything just works.

![Avro Phonetic Manager](screenshot.png)

---

## What's Fixed (Detailed)

### 1. Left Shift Key Bug (Critical)

**The problem:** When Avro Phonetic is active, the Left Shift key stops working **everywhere** — you can't capitalise letters, can't use Shift+Click to select text, nothing. This affects every application on the system, not just the one you're typing Bangla in.

**Root cause:** In `main-gjs.js`, the engine intercepts keycode 42 (Left Shift) and returns `true`, which tells iBus "I handled this key" — so the system never sees it. The code was meant to track Shift state for phonetic rules but the implementation consumes the key entirely.

**The fix:** Changed `return true` to `return false` for keycode 42 (Left Shift) and added keycode 54 (Right Shift) with the same fix. The keys pass through to the system while Avro still processes the phonetic input correctly.

### 2. Preferences Window Broken on GNOME 42+ (Medium)

**The problem:** The preferences dialog uses GTK3 which looks broken or refuses to open on modern GNOME desktops (GNOME 42+, Ubuntu 22.04+). The UI is misaligned and doesn't follow the system theme.

**The fix:** Complete rewrite of `pref.js` using GTK4 and libadwaita. The preferences now use modern GNOME widgets (SwitchRow, SpinRow, PreferencesGroup) and look native on any current GNOME desktop.

### 3. Input Switching Broken on Wayland (Medium)

**The problem:** On Wayland (default since Ubuntu 21.10), iBus cannot grab global keyboard shortcuts because Wayland doesn't allow X11-style key grabs. The default iBus hotkey (Super+Space or Ctrl+Space) simply doesn't work.

**The fix:** Configures GNOME's native input source switching via gsettings (`Super+Space` to switch, `Shift+Super+Space` to switch back). Creates an autostart entry so the shortcuts persist across reboots and dconf resets.

### 4. System Updates Break Fixes (Low)

**The problem:** When `apt upgrade` updates the `ibus-avro` package, it overwrites `main-gjs.js` with the upstream version, bringing back the Left Shift bug.

**The fix:** Installs an APT hook (`/etc/apt/apt.conf.d/99-fix-ibus-avro`) that automatically re-applies the Shift fix and disables debug logging after every apt install/upgrade.

### 5. Debug Logging Spam (Low)

**The problem:** Every single keypress is logged via `print()` to the system journal, creating massive log spam that fills disk space and slows down `journalctl`.

**The fix:** All debug `print()` statements are commented out (except the IBus bus connection error message which is actually useful).

### Summary Table

| Bug | Severity | Upstream | This Fork |
|-----|----------|----------|-----------|
| Left Shift key broken | Critical | Consumes keycode 42 | Passes through |
| Right Shift key | Critical | Not handled | Passes through |
| Preferences window | Medium | GTK3, broken on GNOME 42+ | GTK4 + libadwaita |
| Wayland switching | Medium | X11 key grabs, broken | GNOME gsettings |
| Updates break fixes | Low | No solution | APT hook auto-fixes |
| Debug log spam | Low | Every keypress logged | Disabled |

---

## Supported Systems

- Ubuntu 24.04 LTS (Noble Numbat)
- Ubuntu 26.04 LTS (Resolute Reedbuck)
- Debian 12 (Bookworm) and newer
- Linux Mint 21+ / Pop!_OS 22.04+
- Any Debian-based distro with iBus and GNOME

---

## Installation Guide

### Prerequisites

You need:
- Ubuntu 24.04 or later (or any supported distro listed above)
- A terminal (press `Ctrl+Alt+T` to open one)
- Internet connection (to download the package)

### Step 1: Install Git (if not already installed)

```bash
sudo apt install -y git
```

### Step 2: Download this project

```bash
git clone https://github.com/mmhfarooque/ibus-avro-fixed.git
```

### Step 3: Enter the project folder

```bash
cd ibus-avro-fixed
```

### Step 4: Make the installer executable

```bash
chmod +x install.sh setup-gui.sh
```

### Step 5: Run the installer

```bash
./install.sh
```

This will:
- Install `ibus-avro` from Ubuntu repositories (if not already installed)
- Install GTK4/libadwaita dependencies for the new preferences window
- Apply the Left Shift and Right Shift key fix
- Disable debug keypress logging
- Install the modern GTK4 preferences window
- Create an APT hook so fixes survive system updates
- Configure Super+Space input switching for Wayland
- Create an autostart entry so shortcuts persist across reboots
- Restart iBus

### Step 6: Add Bangla as an input source

1. Open **Settings** (click the gear icon in the top-right system menu)
2. Go to **Keyboard**
3. Under **Input Sources**, click the **+** button
4. Search for **Bangla**
5. Select **Bangla (Avro Phonetic)**
6. Click **Add**

You should now see two input sources: **English (US)** and **Bangla (Avro Phonetic)**.

### Step 7: Test it

1. Press **Super+Space** — the input source indicator in the top bar should change
2. Open any text editor or browser
3. Type `ami bangla likhte pari` — you should see: আমি বাংলা লিখতে পারি
4. Press **Super+Space** again to switch back to English

### Step 8 (Optional): Install the GUI Manager

```bash
./setup-gui.sh
```

Then search **"Avro"** in your app launcher, or run:

```bash
python3 avro-manager.py
```

---

## Alternative: Install via .deb Package

If you prefer a traditional package install:

1. Go to [Releases](https://github.com/mmhfarooque/ibus-avro-fixed/releases)
2. Download `ibus-avro-fixed_2.1.1_all.deb`
3. Open a terminal in your Downloads folder
4. Run:

```bash
sudo apt install ./ibus-avro-fixed_2.1.1_all.deb
```

This **replaces** the upstream `ibus-avro` package with the fixed version. Then follow Steps 6-8 above.

To remove: `sudo apt remove ibus-avro-fixed`

---

## GUI Manager

The Avro Phonetic Manager is a full GTK4/libadwaita graphical application for managing your Avro installation.

### Features

**Status Panel**
- iBus daemon: running or not
- Avro engine: installed, registered with iBus
- Session type: Wayland or X11
- Input sources: shows your configured keyboard layouts

**Input Switching**
- Current Super+Space shortcut display
- One-click "Configure Super+Space Switching" button
- Automatic autostart entry for reboot persistence

**Typing Settings**
- Preview Window: show/hide suggestion preview while typing
- Enter Closes Preview Only: Enter commits without newline
- Dictionary Suggestions: enable Bangla word suggestions
- Max Suggestions: number of candidates (5-15)
- Suggestion List Orientation: horizontal or vertical
- Apply button saves all settings instantly

**Fix Status Dashboard**
- Left/Right Shift Fix: Applied or Not applied
- Debug Logging Disabled: Applied or Not applied
- GTK4 Preferences: Applied or Not applied
- Wayland Switching: Applied or Not applied
- APT Hook (Persistence): Applied or Not applied
- "Apply All Fixes" button to fix everything in one click

**Maintenance**
- Restart IBus: restart the input method framework
- Avro Preferences: open the lightweight preferences dialog
- Add Bangla Input Source: opens GNOME Keyboard Settings directly
- Restore Upstream: remove all fixes and go back to stock ibus-avro

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
| Super+Space doesn't switch | Open the GUI Manager → click "Configure Super+Space Switching". Or run: `gsettings set org.gnome.desktop.wm.keybindings switch-input-source "['<Super>space']"` |
| Left Shift still broken | Open the GUI Manager → click "Apply All Fixes". Or run: `./apply-fix-now.sh` |
| Avro not in input source list | Run `ibus restart`, then add it in Settings → Keyboard → Input Sources |
| Fixes disappear after update | The APT hook should handle this. If not, run `./install.sh` again |
| Preferences window won't open | Make sure `gir1.2-gtk-4.0` and `gir1.2-adw-1` are installed: `sudo apt install -y gir1.2-gtk-4.0 gir1.2-adw-1` |
| GUI Manager won't launch | Install Python GTK4 bindings: `sudo apt install -y python3-gi gir1.2-gtk-4.0 gir1.2-adw-1` |
| Nothing works after reboot | Log out and log back in. iBus starts on login. |

---

## Complete Setup (Copy-Paste)

For those who want the entire setup in one block:

```bash
# Download
git clone https://github.com/mmhfarooque/ibus-avro-fixed.git
cd ibus-avro-fixed

# Install driver + all fixes
chmod +x install.sh setup-gui.sh
./install.sh

# Install GUI manager (optional)
./setup-gui.sh

# Add Bangla input source (if not already added)
gsettings set org.gnome.desktop.input-sources sources "[('xkb', 'us'), ('ibus', 'ibus-avro')]"

# Restart iBus
ibus restart

# Test: press Super+Space to switch, then type in any app
```

---

## File Structure

```
.
├── install.sh              # One-command installer (handles everything)
├── uninstall.sh            # Restore upstream ibus-avro
├── apply-fix-now.sh        # Quick manual fix (sudo required)
├── setup-wayland.sh        # Wayland input switching setup
├── avro-manager.py         # Full GTK4 GUI manager
├── setup-gui.sh            # GUI dependency installer + desktop shortcut
├── main-gjs.js             # IBus engine (with Shift fix)
├── pref.js                 # Preferences dialog (GTK4/libadwaita)
├── avrolib.js              # Phonetic transliteration library
├── avroregexlib.js         # Regex-based transliteration rules
├── autocorrect.js          # Autocorrect dictionary
├── avrodict.js             # Bangla dictionary (7MB)
├── suggestionbuilder.js    # Suggestion engine
├── dbsearch.js             # Dictionary search
├── levenshtein.js          # Edit distance for fuzzy matching
├── suffixdict.js           # Suffix dictionary
├── utf8.js                 # UTF-8 utilities
├── packaging/
│   └── build-deb.sh        # Build .deb package
├── screenshot.png          # GUI Manager screenshot
├── VERSION                 # Current version
├── CHANGELOG.md            # Version history
├── LICENSE                 # MPL 2.0
└── README.md
```

---

## Uninstall

To remove all fixes and restore upstream ibus-avro:

```bash
./uninstall.sh
```

Or if installed via .deb:

```bash
sudo apt remove ibus-avro-fixed
sudo apt install ibus-avro
```

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for full version history.

---

## Credits

- **Original:** [Sarim Khan](https://github.com/sarim/ibus-avro) — ibus-avro engine and phonetic library
- **Contributors:** Mehdi Hasan Khan (dictionary support)
- **Fixes, GTK4 port, GUI Manager:** [Mahmud Farooque](https://github.com/mmhfarooque)

## License

MPL 2.0 (same as upstream ibus-avro)
