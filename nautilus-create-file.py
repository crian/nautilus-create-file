# SPDX-License-Identifier: GPL-3.0-or-later
"""Nautilus extension: add "Create New File…" to the context menu."""

import gettext
import os
from typing import List, Optional

import gi

# Gtk and Adwaita are required
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Nautilus", "4.1")
from gi.repository import Adw, Gio, GLib, GObject, Gtk, Nautilus

DEFAULT_NAME = "new-file.txt"

# Virtual locations where files can't be created
UNSUPPORTED_SCHEMES = frozenset(
    {"trash", "recent", "starred", "x-nautilus-search", "other-locations"}
)

# Delay before checking whether a name exists, so typing doesn't trigger I/O per key
EXISTS_CHECK_DELAY_MS = 150

# --- Localization (standard gettext) -------------------------------------
# Catalogs are searched as <localedir>/<lang>/LC_MESSAGES/<domain>.mo in:
#   1. "locale/" next to this file
#   2. ~/.local/share/locale
#   3. /usr/share/locale
GETTEXT_DOMAIN = "nautilus-create-file"


def _load_translation() -> gettext.GNUTranslations:
    """Load the gettext translation for the session language.

    Searches the locale directories next to the script, in the user data
    directory, and in /usr/share/locale. Falls back to the English source
    strings if no catalog is found.
    """
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


def _can_create_in(location: Gio.File) -> bool:
    """Return True if *location* is a place where a file could be created."""
    return location.get_uri_scheme() not in UNSUPPORTED_SCHEMES


class CreateFileExtension(GObject.GObject, Nautilus.MenuProvider):
    """Nautilus extension providing a "Create New File…" context menu entry."""

    def __init__(self) -> None:
        super().__init__()
        self._dialog_open: bool = False
        self._check_source: int = 0  # pending debounce timeout, 0 if none
        self._check_id: int = 0  # bumped to invalidate in-flight checks

    # ------------------------------------------------------------------
    # Menu entries
    # ------------------------------------------------------------------
    def _make_item(self, name: str, location: Gio.File) -> Nautilus.MenuItem:
        """Create a menu item that opens the new-file dialog for *location*."""
        item = Nautilus.MenuItem(
            name=name,
            label=_("Create New File…"),
            tip=_("Enter a name and extension to create a file"),
        )
        item.connect("activate", self._on_activate, location)
        return item

    def get_background_items(self, current_folder: Nautilus.FileInfo) -> List[Nautilus.MenuItem]:
        """Return menu items for the folder background context menu."""
        location = current_folder.get_location()
        if location is None or not _can_create_in(location):
            return []
        return [self._make_item("CreateFileExtension::Create", location)]

    def get_file_items(self, files: List[Nautilus.FileInfo]) -> List[Nautilus.MenuItem]:
        """Return menu items when exactly one folder is selected."""
        # Offer the entry when exactly one folder is selected
        if len(files) != 1 or not files[0].is_directory():
            return []
        location = files[0].get_location()
        if location is None or not _can_create_in(location):
            return []
        return [self._make_item("CreateFileExtension::CreateInFolder", location)]

    # ------------------------------------------------------------------
    # Dialog
    # ------------------------------------------------------------------
    def _on_activate(
        self,
        _item: Nautilus.MenuItem,
        folder: Gio.File,
    ) -> None:
        """Open the "New File" dialog for *folder*."""
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

        def _focus() -> bool:
            entry.grab_focus()
            entry.select_region(0, stem_len)
            return False

        GLib.idle_add(_focus)

    def _on_closed(self, _dialog: Adw.AlertDialog) -> None:
        """Reset the dialog-open flag when the dialog is closed."""
        self._cancel_pending_check()
        self._dialog_open = False

    def _cancel_pending_check(self) -> None:
        """Drop the debounce timeout and ignore results of running checks."""
        if self._check_source:
            GLib.source_remove(self._check_source)
            self._check_source = 0
        self._check_id += 1

    def _set_validation(
        self,
        entry: Gtk.Entry,
        dialog: Adw.AlertDialog,
        error: Optional[str],
        ok: bool,
    ) -> None:
        """Show *error* (if any) and enable "Create" only when *ok*."""
        if error:
            entry.add_css_class("error")
        else:
            entry.remove_css_class("error")
        dialog.set_body(error or _("Enter a file name:"))
        dialog.set_response_enabled("create", ok)

    def _on_changed(
        self,
        entry: Gtk.Entry,
        dialog: Adw.AlertDialog,
        folder: Gio.File,
    ) -> None:
        """Validate the entry text; the existence check runs asynchronously."""
        name = entry.get_text().strip()
        self._cancel_pending_check()

        error: Optional[str] = None
        if not name:
            error = _("Please enter a file name.")
        elif "/" in name or "\0" in name:
            error = _("Invalid file name.")
        elif name in (".", "..") or all(c == "." for c in name):
            error = _("Invalid file name.")

        if error:
            self._set_validation(entry, dialog, error, False)
            return

        # Name looks valid: keep "Create" disabled until the check finished
        self._set_validation(entry, dialog, None, False)
        self._check_source = GLib.timeout_add(
            EXISTS_CHECK_DELAY_MS,
            self._start_exists_check,
            entry,
            dialog,
            folder,
            name,
            self._check_id,
        )

    def _start_exists_check(
        self,
        entry: Gtk.Entry,
        dialog: Adw.AlertDialog,
        folder: Gio.File,
        name: str,
        check_id: int,
    ) -> bool:
        """Query whether *name* already exists in *folder* (debounced)."""
        self._check_source = 0
        try:
            target = folder.get_child_for_display_name(name)
        except GLib.Error:
            # Some backends reject names that the checks above let through
            self._set_validation(entry, dialog, _("Invalid file name."), False)
            return GLib.SOURCE_REMOVE

        target.query_info_async(
            "standard::name",
            Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
            GLib.PRIORITY_DEFAULT,
            None,
            self._on_exists_checked,
            (entry, dialog, name, check_id),
        )
        return GLib.SOURCE_REMOVE

    def _on_exists_checked(
        self,
        target: Gio.File,
        result: Gio.AsyncResult,
        data: tuple,
    ) -> None:
        """Apply the result of the existence check, unless it is outdated."""
        entry, dialog, name, check_id = data
        if check_id != self._check_id:
            return
        try:
            target.query_info_finish(result)
        except GLib.Error:
            # Not found (or not queryable): real errors surface on creation
            self._set_validation(entry, dialog, None, True)
            return
        error = _("“{name}” already exists.").format(name=name)
        self._set_validation(entry, dialog, error, False)

    # ------------------------------------------------------------------
    # File creation (asynchronous, so slow network mounts don't block Nautilus)
    # ------------------------------------------------------------------
    def _on_response(
        self,
        _dialog: Adw.AlertDialog,
        response: str,
        entry: Gtk.Entry,
        folder: Gio.File,
        parent: Optional[Gtk.Window],
    ) -> None:
        """Handle the dialog response and create the file if requested."""
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
            self._show_error(parent, str(e))

    def _on_created(
        self,
        target: Gio.File,
        result: Gio.AsyncResult,
        parent: Optional[Gtk.Window],
    ) -> None:
        """Finish asynchronous file creation and close the stream asynchronously."""
        try:
            stream = target.create_finish(result)
        except GLib.Error as e:
            self._show_error(parent, str(e))
            return
        stream.close_async(
            GLib.PRIORITY_DEFAULT, None, self._on_stream_closed, parent
        )

    def _on_stream_closed(
        self,
        stream: Gio.OutputStream,
        result: Gio.AsyncResult,
        parent: Optional[Gtk.Window],
    ) -> None:
        """Finish closing the new file's stream (commits it on remote mounts)."""
        try:
            stream.close_finish(result)
        except GLib.Error as e:
            self._show_error(parent, str(e))

    def _show_error(self, parent: Optional[Gtk.Window], message: str) -> None:
        """Show an error dialog with *message* to the user."""
        dialog = Adw.AlertDialog(heading=_("Creation Error"), body=message)
        dialog.add_response("ok", _("OK"))
        dialog.present(parent)
