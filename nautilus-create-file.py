# SPDX-License-Identifier: GPL-3.0-or-later
import gettext
import os

import gi

# Gtk and Adwaita are required
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
# Nautilus 4.1 is used by current GNOME releases, 4.0 by older ones
try:
    gi.require_version("Nautilus", "4.1")
except ValueError:
    gi.require_version("Nautilus", "4.0")
from gi.repository import Adw, Gio, GLib, GObject, Gtk, Nautilus

DEFAULT_NAME = "new-file.txt"

# --- Localization (standard gettext) -------------------------------------
# Catalogs are searched as <localedir>/<lang>/LC_MESSAGES/<domain>.mo in:
#   1. "locale/" next to this file
#   2. ~/.local/share/locale
#   3. /usr/share/locale
GETTEXT_DOMAIN = "nautilus-create-file"


def _load_translation():
    here = [
        os.path.dirname(os.path.abspath(__file__)),
        os.path.dirname(os.path.realpath(__file__)),  # in case of a symlink
    ]
    localedirs = [os.path.join(d, "locale") for d in dict.fromkeys(here)]
    localedirs.append(os.path.join(GLib.get_user_data_dir(), "locale"))
    localedirs.append("/usr/share/locale")

    # e.g. ["de_DE.UTF-8", "de_DE", "de.UTF-8", "de"] from the session locale
    languages = [lang for lang in GLib.get_language_names() if lang != "C"]

    for localedir in localedirs:
        try:
            return gettext.translation(GETTEXT_DOMAIN, localedir, languages=languages)
        except OSError:
            continue
    return gettext.NullTranslations()  # fall back to the English source strings


_ = _load_translation().gettext


class CreateFileExtension(GObject.GObject, Nautilus.MenuProvider):
    def __init__(self):
        super().__init__()
        self._dialog_open = False

    # ------------------------------------------------------------------
    # Menu entries
    # ------------------------------------------------------------------
    def _make_item(self, name, location):
        item = Nautilus.MenuItem(
            name=name,
            label=_("Create New File…"),
            tip=_("Enter a name and extension to create a file"),
        )
        item.connect("activate", self._on_activate, location)
        return item

    def get_background_items(self, current_folder):
        location = current_folder.get_location()
        if location is None:
            return []
        return [self._make_item("CreateFileExtension::Create", location)]

    def get_file_items(self, files):
        # Offer the entry when exactly one folder is selected
        if len(files) != 1 or not files[0].is_directory():
            return []
        location = files[0].get_location()
        if location is None:
            return []
        return [self._make_item("CreateFileExtension::CreateInFolder", location)]

    # ------------------------------------------------------------------
    # Dialog
    # ------------------------------------------------------------------
    def _on_activate(self, _item, folder):
        # Prevent multiple dialogs from rapid double-clicks
        if self._dialog_open:
            return
        self._dialog_open = True

        app = Gtk.Application.get_default()
        parent = app.get_active_window() if app else None

        dialog = Adw.AlertDialog(
            heading=_("New File"),
            body=_("Enter a file name:"),
        )
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("create", _("Create"))
        dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("create")
        dialog.set_close_response("cancel")
        dialog.set_response_enabled("create", False)

        entry = Gtk.Entry(text=DEFAULT_NAME, activates_default=True)
        entry.connect("changed", self._on_changed, dialog, folder)
        dialog.set_extra_child(entry)

        dialog.connect("response", self._on_response, entry, folder, parent)
        dialog.connect("closed", self._on_closed)

        # Initial validation (the default name may already exist)
        self._on_changed(entry, dialog, folder)

        dialog.present(parent)

        # Focus the entry and select only the file stem, like renaming in Nautilus
        stem_len = len(DEFAULT_NAME.rsplit(".", 1)[0])

        def _focus():
            entry.grab_focus()
            entry.select_region(0, stem_len)
            return False

        GLib.idle_add(_focus)

    def _on_closed(self, _dialog):
        self._dialog_open = False

    def _on_changed(self, entry, dialog, folder):
        name = entry.get_text().strip()
        error = None

        if name in (".", "..") or "/" in name:
            error = _("Invalid file name.")
        elif name and folder.get_child(name).query_exists(None):
            error = _("“{name}” already exists.").format(name=name)

        if error:
            entry.add_css_class("error")
        else:
            entry.remove_css_class("error")

        dialog.set_body(error or _("Enter a file name:"))
        dialog.set_response_enabled("create", bool(name) and error is None)

    # ------------------------------------------------------------------
    # File creation (asynchronous, so slow network mounts don't block Nautilus)
    # ------------------------------------------------------------------
    def _on_response(self, _dialog, response, entry, folder, parent):
        if response != "create":
            return

        name = entry.get_text().strip()
        try:
            target = folder.get_child_for_display_name(name)
            target.create_async(
                Gio.FileCreateFlags.NONE,
                GLib.PRIORITY_DEFAULT,
                None,
                self._on_created,
                parent,
            )
        except GLib.Error as e:
            self._show_error(parent, e.message)

    def _on_created(self, target, result, parent):
        try:
            stream = target.create_finish(result)
            stream.close(None)
        except GLib.Error as e:
            self._show_error(parent, e.message)

    def _show_error(self, parent, message):
        dialog = Adw.AlertDialog(heading=_("Creation Error"), body=message)
        dialog.add_response("ok", _("OK"))
        dialog.present(parent)
