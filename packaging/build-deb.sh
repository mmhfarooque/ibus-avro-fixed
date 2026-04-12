#!/bin/bash
# ============================================================================
# Build .deb package for ibus-avro-fixed
# ============================================================================
# Creates a .deb that installs the fixed ibus-avro alongside (or replacing)
# the upstream package.
#
# Usage: ./packaging/build-deb.sh
# Output: ./ibus-avro-fixed_2.0.0_all.deb
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION=$(cat "$PROJECT_DIR/VERSION" 2>/dev/null | tr -d '[:space:]' || echo "2.0.0")
PKG_NAME="ibus-avro-fixed"
PKG_DIR="$PROJECT_DIR/build/${PKG_NAME}_${VERSION}_all"
DEB_OUTPUT="$PROJECT_DIR/${PKG_NAME}_${VERSION}_all.deb"
INSTALL_DIR="usr/share/ibus-avro"

echo ""
echo "=== Building $PKG_NAME .deb v$VERSION ==="
echo ""

# ---- Create package structure ----
rm -rf "$PKG_DIR"
mkdir -p "$PKG_DIR/DEBIAN"
mkdir -p "$PKG_DIR/$INSTALL_DIR"
mkdir -p "$PKG_DIR/usr/share/ibus/component"
mkdir -p "$PKG_DIR/usr/share/glib-2.0/schemas"
mkdir -p "$PKG_DIR/usr/share/applications"
mkdir -p "$PKG_DIR/usr/share/metainfo"
mkdir -p "$PKG_DIR/usr/share/doc/$PKG_NAME"
mkdir -p "$PKG_DIR/usr/local/bin"
mkdir -p "$PKG_DIR/etc/apt/apt.conf.d"

# ---- Copy source files ----
echo "[1/3] Copying files..."

# Engine and library files
for f in main-gjs.js pref.js avrolib.js avroregexlib.js autocorrect.js \
         avrodict.js dbsearch.js evars.js.in levenshtein.js suffixdict.js \
         suggestionbuilder.js utf8.js avro-bangla.png; do
    if [ -f "$PROJECT_DIR/$f" ]; then
        cp "$PROJECT_DIR/$f" "$PKG_DIR/$INSTALL_DIR/"
    fi
done

# Generate evars.js from template
cat > "$PKG_DIR/$INSTALL_DIR/evars.js" << 'EVARS'
function get_pkgdatadir(){
return "/usr/share/ibus-avro";
}
function get_libexecdir(){
return "/usr/libexec";
}
EVARS

# UI file (kept for backwards compat, though GTK4 prefs don't use it)
cp "$PROJECT_DIR/avropref.ui" "$PKG_DIR/$INSTALL_DIR/" 2>/dev/null || true

# IBus component XML
sed "s|\${pkgdatadir}|/usr/share/ibus-avro|g" "$PROJECT_DIR/ibus-avro.xml.in" \
    > "$PKG_DIR/usr/share/ibus/component/ibus-avro.xml"

# GSettings schema
cp "$PROJECT_DIR/com.omicronlab.avro.gschema.xml" "$PKG_DIR/usr/share/glib-2.0/schemas/"

# Desktop file
sed "s|\${pkgdatadir}|/usr/share/ibus-avro|g" "$PROJECT_DIR/ibus-setup-ibus-avro.desktop.in" \
    > "$PKG_DIR/usr/share/applications/ibus-setup-ibus-avro.desktop"

# Metainfo
cp "$PROJECT_DIR/com.github.sarim.ibus.avro.metainfo.xml" "$PKG_DIR/usr/share/metainfo/" 2>/dev/null || true

# Docs
cp "$PROJECT_DIR/README.md" "$PKG_DIR/usr/share/doc/$PKG_NAME/"
cp "$PROJECT_DIR/CHANGELOG.md" "$PKG_DIR/usr/share/doc/$PKG_NAME/" 2>/dev/null || true
cp "$PROJECT_DIR/LICENSE" "$PKG_DIR/usr/share/doc/$PKG_NAME/copyright"

# APT hook for persistence
cat > "$PKG_DIR/usr/local/bin/fix-ibus-avro.sh" << 'PATCHSCRIPT'
#!/bin/bash
FILE="/usr/share/ibus-avro/main-gjs.js"
if [ -f "$FILE" ]; then
    if grep -q 'keycode == 42) { return true' "$FILE"; then
        sed -i 's/if (keycode == 42) { return true; }/if (keycode == 42 || keycode == 54) { return false; }/' "$FILE"
    fi
    sed -i 's|^\(\s*\)print(keyval|\1//print(keyval|' "$FILE"
fi
PATCHSCRIPT
chmod 755 "$PKG_DIR/usr/local/bin/fix-ibus-avro.sh"

cat > "$PKG_DIR/etc/apt/apt.conf.d/99-fix-ibus-avro" << 'HOOK'
DPkg::Post-Invoke { "/usr/local/bin/fix-ibus-avro.sh || true"; };
HOOK

echo "  Files copied"

# ---- Create debian control files ----
echo "[2/3] Creating package metadata..."

INSTALLED_SIZE=$(du -sk "$PKG_DIR" 2>/dev/null | awk '{print $1}')

cat > "$PKG_DIR/DEBIAN/control" << EOF
Package: $PKG_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: all
Depends: gjs, ibus, dconf-gsettings-backend | gsettings-backend, gir1.2-gtk-4.0, gir1.2-adw-1
Conflicts: ibus-avro
Replaces: ibus-avro
Provides: ibus-avro
Installed-Size: $INSTALLED_SIZE
Maintainer: Mahmud Farooque <farooque7@gmail.com>
Homepage: https://github.com/mmhfarooque/ibus-avro-fixed
Description: Avro Phonetic Bangla input method for IBus — Fixed Edition
 Avro Phonetic transliterates English keystrokes to Bangla. This is a
 fixed fork of ibus-avro with the following improvements:
 .
 - Left Shift / Right Shift key bug fixed (no longer consumed by engine)
 - GTK4/libadwaita preferences window (modern GNOME look)
 - Wayland input switching support (Super+Space)
 - APT hook to re-apply fixes after system updates
 - Debug keypress logging disabled
 .
 Based on sarim/ibus-avro. Licensed under MPL 2.0.
EOF

# postinst
cat > "$PKG_DIR/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e

# Compile GSettings schema
glib-compile-schemas /usr/share/glib-2.0/schemas/ 2>/dev/null || true

# Restart iBus
ibus restart 2>/dev/null || true

echo ""
echo "============================================"
echo "  Avro Phonetic (Fixed Edition) installed!"
echo "============================================"
echo ""
echo "  1. Add 'Bangla (Avro Phonetic)' in Settings → Keyboard"
echo "  2. Press Super+Space to switch"
echo "  3. Log out and back in if iBus doesn't pick it up"
echo ""
EOF
chmod 755 "$PKG_DIR/DEBIAN/postinst"

# postrm
cat > "$PKG_DIR/DEBIAN/postrm" << 'EOF'
#!/bin/bash
set -e
glib-compile-schemas /usr/share/glib-2.0/schemas/ 2>/dev/null || true
ibus restart 2>/dev/null || true
EOF
chmod 755 "$PKG_DIR/DEBIAN/postrm"

# ---- Build ----
echo "[3/3] Building .deb..."
dpkg-deb --root-owner-group --build "$PKG_DIR" "$DEB_OUTPUT"

rm -rf "$PROJECT_DIR/build"

echo ""
echo "============================================"
echo "  Package: $DEB_OUTPUT"
echo "============================================"
echo ""
echo "  Install: sudo apt install ./$DEB_OUTPUT"
echo "  Remove:  sudo apt remove $PKG_NAME"
echo ""
