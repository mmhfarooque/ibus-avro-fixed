# ibus-avro-fixed — Avro Phonetic Bangla for Linux (Fixed Edition)

Avro Phonetic lets you type Bangla by writing English phonetically — it transliterates as you type. This is a **fixed fork** of [ibus-avro](https://github.com/sarim/ibus-avro) that solves all known bugs on modern Ubuntu/Debian.

## What's Fixed

| Bug | Upstream | This Fork |
|-----|----------|-----------|
| **Left Shift key broken** | Engine consumes keycode 42 — Left Shift stops working system-wide | Fixed: passes through correctly |
| **Right Shift key** | Not handled | Fixed: passes through correctly |
| **Preferences window** | GTK3 (outdated, looks wrong on GNOME 42+) | GTK4 + libadwaita (modern GNOME look) |
| **Wayland input switching** | Relies on X11 key grabs (broken on Wayland) | Configures GNOME Super+Space switching |
| **System updates break fixes** | No solution | APT hook re-applies fixes automatically |
| **Debug logging** | Every keypress logged to journal | Disabled |

## Supported Systems

- Ubuntu 24.04 LTS, 26.04 LTS
- Debian 12+
- Linux Mint 21+
- Pop!_OS 22.04+
- Any Debian-based distro with iBus and GNOME

## Quick Install

### Option 1: One-command installer (recommended)

```bash
git clone https://github.com/mmhfarooque/ibus-avro-fixed.git
cd ibus-avro-fixed
chmod +x install.sh
./install.sh
```

This handles everything — installs ibus-avro if missing, applies all fixes, sets up Wayland switching, creates APT hook for persistence.

### Option 2: .deb package

Download from [Releases](https://github.com/mmhfarooque/ibus-avro-fixed/releases), then:

```bash
sudo apt install ./ibus-avro-fixed_2.0.0_all.deb
```

This **replaces** the upstream `ibus-avro` package with the fixed version.

### Option 3: Patch existing ibus-avro

If you already have `ibus-avro` installed and just want the fixes:

```bash
git clone https://github.com/mmhfarooque/ibus-avro-fixed.git
cd ibus-avro-fixed
./install.sh
```

The installer detects the existing installation and applies fixes on top.

## After Installation

1. Open **Settings → Keyboard → Input Sources**
2. Click **+** → search **Bangla** → select **Bangla (Avro Phonetic)**
3. Press **Super+Space** to switch between English and Bangla
4. Type in English — Avro converts to Bangla phonetically

## How Avro Phonetic Works

Type English letters and Avro converts them to Bangla:

| You type | You get |
|----------|---------|
| `ami` | আমি |
| `bangla` | বাংলা |
| `bhalo` | ভালো |
| `dhaka` | ঢাকা |
| `tumi kemon acho` | তুমি কেমন আছো |

Full phonetic rules: [Avro Phonetic Layout](https://avro.im/layout)

## Preferences

Right-click the iBus tray icon → **Preferences**, or run:

```bash
gjs --include-path=/usr/share/ibus-avro /usr/share/ibus-avro/pref.js --standalone
```

Settings:
- **Preview Window** — show/hide suggestion preview while typing
- **Dictionary Suggestions** — enable Bangla word suggestions
- **Max Suggestions** — number of candidates (5–15)
- **Enter Closes Preview** — Enter commits without newline
- **Orientation** — horizontal or vertical suggestion list

## File Structure

```
.
├── install.sh              # One-command installer
├── uninstall.sh            # Restore upstream ibus-avro
├── setup-wayland.sh        # Wayland input switching setup
├── main-gjs.js             # IBus engine (with Shift fix)
├── pref.js                 # Preferences GUI (GTK4/libadwaita)
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
├── VERSION
├── CHANGELOG.md
├── LICENSE                  # MPL 2.0
└── README.md
```

## Uninstall

To restore upstream ibus-avro:

```bash
./uninstall.sh
```

Or if installed via .deb:

```bash
sudo apt remove ibus-avro-fixed
sudo apt install ibus-avro
```

## Credits

- **Original:** [Sarim Khan](https://github.com/sarim/ibus-avro) — ibus-avro engine and phonetic library
- **Contributors:** Mehdi Hasan Khan (dictionary support)
- **Fixes & GTK4 port:** [Mahmud Farooque](https://github.com/mmhfarooque)

## License

MPL 2.0 (same as upstream ibus-avro)
