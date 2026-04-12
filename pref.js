/*
    =============================================================================
    *****************************************************************************
    This Source Code Form is subject to the terms of the Mozilla Public
    License, v. 2.0. If a copy of the MPL was not distributed with this
    file, You can obtain one at https://mozilla.org/MPL/2.0/.

    The Original Code is ibus-avro
    The Initial Developer is Sarim Khan <sarim2005@gmail.com>
    Copyright (C) Sarim Khan. All Rights Reserved.

    Contributors:
        Mehdi Hasan Khan <mhasan@omicronlab.com>
        Mahmud Farooque <farooque7@gmail.com> (GTK4/libadwaita port)

    *****************************************************************************
    =============================================================================
*/

imports.gi.versions.Gtk = '4.0';
imports.gi.versions.Adw = '1';
imports.searchPath.unshift('.');
const Gio = imports.gi.Gio;
const Gtk = imports.gi.Gtk;
const Adw = imports.gi.Adw;
const eevars = imports.evars;

var prefwindow, switch_preview, switch_newline, switch_dict;

function runpref() {

    let app = new Adw.Application({
        application_id: 'com.omicronlab.avro.preferences',
        flags: Gio.ApplicationFlags.FLAGS_NONE,
    });

    app.connect('activate', function() {
        let setting = Gio.Settings.new("com.omicronlab.avro");

        // Main window
        prefwindow = new Adw.ApplicationWindow({
            application: app,
            title: 'Avro Phonetic Preferences',
            default_width: 500,
            default_height: 450,
            resizable: false,
        });

        // Toolbar view with header
        let toolbarView = new Adw.ToolbarView();
        prefwindow.set_content(toolbarView);

        let header = new Adw.HeaderBar();
        toolbarView.add_top_bar(header);

        // Scrollable content
        let scroll = new Gtk.ScrolledWindow({ vexpand: true });
        toolbarView.set_content(scroll);

        let mainBox = new Gtk.Box({
            orientation: Gtk.Orientation.VERTICAL,
            spacing: 0,
            margin_start: 16,
            margin_end: 16,
            margin_top: 8,
            margin_bottom: 16,
        });
        scroll.set_child(mainBox);

        // ---- Typing Behaviour ----
        let typingGroup = new Adw.PreferencesGroup({
            title: 'Typing Behaviour',
            description: 'How Avro handles your input',
        });
        mainBox.append(typingGroup);

        // Preview Window toggle
        let previewRow = new Adw.SwitchRow({
            title: 'Preview Window',
            subtitle: 'Show suggestion preview while typing',
        });
        setting.bind("switch-preview", previewRow, "active", Gio.SettingsBindFlags.DEFAULT);
        typingGroup.add(previewRow);
        switch_preview = previewRow;

        // Enter closes preview
        let newlineRow = new Adw.SwitchRow({
            title: 'Enter Closes Preview Only',
            subtitle: 'Enter/Return commits text without inserting a new line',
        });
        setting.bind("switch-newline", newlineRow, "active", Gio.SettingsBindFlags.DEFAULT);
        typingGroup.add(newlineRow);
        switch_newline = newlineRow;

        // ---- Dictionary ----
        let dictGroup = new Adw.PreferencesGroup({
            title: 'Dictionary',
            description: 'Bangla dictionary suggestion settings',
        });
        mainBox.append(dictGroup);

        // Dictionary toggle
        let dictRow = new Adw.SwitchRow({
            title: 'Dictionary Suggestions',
            subtitle: 'Show Bangla word suggestions from dictionary',
        });
        setting.bind("switch-dict", dictRow, "active", Gio.SettingsBindFlags.DEFAULT);
        dictGroup.add(dictRow);
        switch_dict = dictRow;

        // Max suggestions
        let sugAdj = new Gtk.Adjustment({
            value: setting.get_int('lutable-size'),
            lower: 5,
            upper: 15,
            step_increment: 1,
        });
        let sugRow = new Adw.SpinRow({
            title: 'Max Suggestions',
            subtitle: 'Maximum number of dictionary suggestions (5–15)',
            adjustment: sugAdj,
        });
        setting.bind("lutable-size", sugAdj, "value", Gio.SettingsBindFlags.DEFAULT);
        dictGroup.add(sugRow);

        // Orientation
        let orientGroup = new Adw.PreferencesGroup({
            title: 'Appearance',
        });
        mainBox.append(orientGroup);

        let orientRow = new Adw.ActionRow({
            title: 'Suggestion List Orientation',
            subtitle: 'Direction of the candidate list',
        });

        let orientDropdown = new Gtk.DropDown({
            model: Gtk.StringList.new(['Horizontal', 'Vertical']),
            valign: Gtk.Align.CENTER,
        });
        orientDropdown.set_selected(setting.get_int('cboxorient'));
        orientDropdown.connect('notify::selected', function() {
            setting.set_int('cboxorient', orientDropdown.get_selected());
        });
        orientRow.add_suffix(orientDropdown);
        orientGroup.add(orientRow);

        // ---- About ----
        let aboutGroup = new Adw.PreferencesGroup({
            title: 'About',
        });
        mainBox.append(aboutGroup);

        let aboutRow = new Adw.ActionRow({
            title: 'Avro Phonetic for Linux',
            subtitle: 'Bangla typing with phonetic transliteration\nOriginal: Sarim Khan | Fixes: Mahmud Farooque',
        });
        aboutRow.add_prefix(Gtk.Image.new_from_icon_name('input-keyboard-symbolic'));
        aboutGroup.add(aboutRow);

        // ---- Validation ----
        function validate() {
            let previewOn = previewRow.get_active();
            newlineRow.set_sensitive(previewOn);
            dictRow.set_sensitive(previewOn);
            sugRow.set_sensitive(previewOn && dictRow.get_active());
            orientRow.set_sensitive(previewOn);

            if (!previewOn) {
                newlineRow.set_active(false);
                dictRow.set_active(false);
            }
        }

        previewRow.connect('notify::active', validate);
        dictRow.connect('notify::active', validate);
        validate();

        prefwindow.present();
    });

    app.run([]);
}

//check if running standalone
if(ARGV[0] == '--standalone'){
    runpref();
}
