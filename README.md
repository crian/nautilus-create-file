# nautilus-create-file

A small [Nautilus](https://apps.gnome.org/Nautilus/) (GNOME Files) extension that adds **Create New File…** to the context menu. It opens a native Adwaita dialog where you enter a file name and extension, and creates an empty file in the current folder.

## Features

- Entry in the folder background menu, and when a single folder is selected
- Live validation: the *Create* button stays disabled for empty, invalid or already existing names
- Suggested name `new-file.txt` with only the stem selected, like renaming in Nautilus
- Asynchronous creation, so slow network mounts don't block Nautilus
- Works with any location GIO can write to, not just local paths
- Translatable via standard gettext (German included)

## Requirements

- Nautilus 46 or newer (needs `Adw.AlertDialog`, libadwaita ≥ 1.5)
- [nautilus-python](https://gitlab.gnome.org/GNOME/nautilus-python) for Nautilus 4.x
  - Fedora: `nautilus-python`
  - Arch: `python-nautilus`
  - Debian/Ubuntu: `python3-nautilus`

## Installation

### Per user (no build tools needed)

```sh
git clone https://github.com/<your-user>/nautilus-create-file.git
cd nautilus-create-file
bash install.sh
nautilus -q
```

Uninstall with `bash install.sh uninstall`.

### With Meson

```sh
meson setup build --prefix="$HOME/.local"   # or --prefix=/usr for a system-wide install
meson install -C build
nautilus -q
```

## Translating

The extension uses plain gettext with the domain `nautilus-create-file`.

1. Copy `po/nautilus-create-file.pot` to `po/<lang>.po` (e.g. `po/fr.po`).
2. Set `"Language: <lang>\n"` in the header and fill in the `msgstr` entries.
3. Add `<lang>` to `po/LINGUAS`.
4. Run `python3 compile-translations.py` to test, or just install again.

Pull requests with new translations are welcome.

If you add or change strings in `nautilus-create-file.py`, update the template with:

```sh
xgettext --from-code=UTF-8 -L Python -k_ -o po/nautilus-create-file.pot nautilus-create-file.py
```

## Known limitations

- The newly created file is not selected afterwards (the Nautilus extension API has no hook for this).

## License

GPL-3.0-or-later, see [LICENSE](LICENSE).
