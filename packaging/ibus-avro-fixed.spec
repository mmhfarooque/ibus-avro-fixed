####################################################################
# ibus-avro-fixed — Avro Phonetic Bangla input method for IBus
# RPM packaging for openSUSE / Fedora (fills the gap left by the
# apt-only install.sh). Packages the already-fixed source directly:
# the Left/Right Shift fix is baked into main-gjs.js in this fork.
####################################################################

Name:           ibus-avro-fixed
Version:        2.7.0
Release:        1%{?dist}
Summary:        Avro Phonetic Bangla input method for IBus (fixed fork)

License:        MPL-2.0
URL:            https://github.com/mmhfarooque/ibus-avro-fixed
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch

# Engine runs under gjs and talks to IBus; preferences use GTK4/libadwaita.
Requires:       ibus
Requires:       gjs
Requires:       typelib-1_0-IBus-1_0
Requires:       typelib-1_0-Gtk-4_0
Requires:       typelib-1_0-Adw-1
Requires:       dconf

# Bangla Unicode font so typed text renders as glyphs, not tofu boxes.
# The engine emits Unicode codepoints; a Bengali font is what draws them.
# Same name on openSUSE and Fedora.
Requires:       google-noto-sans-bengali-fonts

# This fork supersedes any distro ibus-avro package.
Provides:       ibus-avro = %{version}-%{release}
Conflicts:      ibus-avro

# glib-compile-schemas in scriptlets
Requires(post):   glib2-tools
Requires(postun): glib2-tools

%global pkgdir %{_datadir}/ibus-avro

%description
Avro Phonetic transliterates English keystrokes to Bangla phonetically.

This is a fixed fork of sarim/ibus-avro that bakes in:
  * Left Shift / Right Shift key fix (keycodes 42 and 54 were consumed
    by the engine; they now pass through)
  * GTK4 / libadwaita preferences window
  * Debug keypress logging disabled
  * Depends on a Bangla Unicode font so output renders, not tofu boxes

The engine is gjs-based and distro-agnostic. This package is the
openSUSE/Fedora counterpart to the project's Debian build; the apt-only
installer's persistence hook is unnecessary here because the fix is part
of the packaged source.

KDE Plasma 6 / Wayland Super+Space switching is a per-user session setting
— run %{pkgdir}/setup-wayland.sh once from your desktop session to bind it.

%prep
%setup -q

%build
# evars.js tells the engine where its files live. Point both pkgdatadir
# and libexecdir at the install dir so the static component (ibus-avro.xml)
# and the engine's own command_line self-registration both resolve to a
# real main-gjs.js.
cat > evars.js <<'EOF'
function get_pkgdatadir(){
return "%{pkgdir}";
}
function get_libexecdir(){
return "%{pkgdir}";
}
EOF

# Render the IBus component + setup desktop file from their .in templates.
sed "s|\${pkgdatadir}|%{pkgdir}|g" ibus-avro.xml.in > ibus-avro.xml
sed "s|\${pkgdatadir}|%{pkgdir}|g" ibus-setup-ibus-avro.desktop.in > ibus-setup-ibus-avro.desktop

# Strip leftover debug print() calls (same transform install.sh applies on
# apt systems), keeping the meaningful "IBus bus not found" message.
sed -i '/Exiting because IBus/!s|^\(\s*\)print\s*(|\1//print(|' main-gjs.js

# Make the bundled KDE helper point at the packaged toggle on PATH
# (/usr/bin) instead of the apt installer's /usr/local/bin location.
sed -i 's#/usr/local/bin/ibus-avro-toggle#%{_bindir}/ibus-avro-toggle#g' setup-wayland.sh

%install
# --- Engine + libraries + assets ---
install -d %{buildroot}%{pkgdir}
install -m 0644 evars.js              %{buildroot}%{pkgdir}/evars.js
install -m 0755 main-gjs.js           %{buildroot}%{pkgdir}/main-gjs.js
install -m 0644 avrolib.js            %{buildroot}%{pkgdir}/avrolib.js
install -m 0644 utf8.js               %{buildroot}%{pkgdir}/utf8.js
install -m 0644 avrodict.js           %{buildroot}%{pkgdir}/avrodict.js
install -m 0644 suffixdict.js         %{buildroot}%{pkgdir}/suffixdict.js
install -m 0644 dbsearch.js           %{buildroot}%{pkgdir}/dbsearch.js
install -m 0644 avroregexlib.js       %{buildroot}%{pkgdir}/avroregexlib.js
install -m 0644 suggestionbuilder.js  %{buildroot}%{pkgdir}/suggestionbuilder.js
install -m 0644 levenshtein.js        %{buildroot}%{pkgdir}/levenshtein.js
install -m 0644 autocorrect.js        %{buildroot}%{pkgdir}/autocorrect.js
install -m 0755 pref.js               %{buildroot}%{pkgdir}/pref.js
install -m 0644 avropref.ui           %{buildroot}%{pkgdir}/avropref.ui
install -m 0644 avro-bangla.png       %{buildroot}%{pkgdir}/avro-bangla.png

# --- KDE/Wayland helper scripts (optional, user-run) ---
install -m 0755 setup-wayland.sh      %{buildroot}%{pkgdir}/setup-wayland.sh
install -d %{buildroot}%{_bindir}
install -m 0755 ibus-avro-toggle.sh   %{buildroot}%{_bindir}/ibus-avro-toggle

# --- IBus component registration ---
install -d %{buildroot}%{_datadir}/ibus/component
install -m 0644 ibus-avro.xml %{buildroot}%{_datadir}/ibus/component/ibus-avro.xml

# --- GSettings schema ---
install -d %{buildroot}%{_datadir}/glib-2.0/schemas
install -m 0644 com.omicronlab.avro.gschema.xml \
    %{buildroot}%{_datadir}/glib-2.0/schemas/com.omicronlab.avro.gschema.xml

# --- AppStream metainfo ---
install -d %{buildroot}%{_datadir}/metainfo
install -m 0644 com.github.sarim.ibus.avro.metainfo.xml \
    %{buildroot}%{_datadir}/metainfo/com.github.sarim.ibus.avro.metainfo.xml

# --- Preferences desktop entry ---
install -d %{buildroot}%{_datadir}/applications
install -m 0644 ibus-setup-ibus-avro.desktop \
    %{buildroot}%{_datadir}/applications/ibus-setup-ibus-avro.desktop

%post
glib-compile-schemas %{_datadir}/glib-2.0/schemas &>/dev/null || :

%postun
glib-compile-schemas %{_datadir}/glib-2.0/schemas &>/dev/null || :

%files
%license LICENSE
%doc README.md CHANGELOG.md
%dir %{pkgdir}
%{pkgdir}/*.js
%{pkgdir}/avropref.ui
%{pkgdir}/avro-bangla.png
%{pkgdir}/setup-wayland.sh
%{_bindir}/ibus-avro-toggle
%{_datadir}/ibus/component/ibus-avro.xml
%{_datadir}/glib-2.0/schemas/com.omicronlab.avro.gschema.xml
%{_datadir}/metainfo/com.github.sarim.ibus.avro.metainfo.xml
%{_datadir}/applications/ibus-setup-ibus-avro.desktop

%changelog
* Sat Jun 27 2026 Mahmud Farooque <farooque7@gmail.com> - 2.7.0-1
- Add Bangla Unicode font dependency (google-noto-sans-bengali-fonts) so a
  fresh install renders Bangla out of the box — no manual font download.

* Sat Jun 27 2026 Mahmud Farooque <farooque7@gmail.com> - 2.6.0-1
- First RPM packaging of ibus-avro-fixed for openSUSE/Fedora.
- Packages the already-applied Left/Right Shift fix; no apt persistence
  hook needed. Excludes the apt-/git-coupled avro-manager.py GUI.
