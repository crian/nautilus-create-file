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

- Nautilus 49 or newer (extension API 4.1; needs `Adw.AlertDialog`, libadwaita ≥ 1.5)
- [nautilus-python](https://gitlab.gnome.org/GNOME/nautilus-python) 4.1 or newer for
  Nautilus 49+ (older 4.0.x releases load the 4.0 API and do not work)
  - Fedora: `nautilus-python`
  - Arch: `python-nautilus`
  - Debian/Ubuntu: `python3-nautilus`
- gettext (provides `msgfmt`) when installing from source, for the translations
  - Fedora: `gettext`
  - Arch: `gettext`
  - Debian/Ubuntu: `gettext`

## Installation

### Per user

```sh
git clone https://github.com/crian/nautilus-create-file.git
cd nautilus-create-file
bash install.sh
nautilus -q
```

Uninstall with `bash install.sh uninstall`.

`install.sh` compiles the catalogs with `msgfmt`. If gettext is not installed,
it skips the translations and installs the extension with English texts only.

### With Meson

```sh
meson setup build --prefix="$HOME/.local"   # or --prefix=/usr for a system-wide install
meson install -C build
nautilus -q
```

## Translating

The extension uses plain gettext with the domain `nautilus-create-file`. The
catalogs in `po/` are compiled with `msgfmt` when installing.

1. Create a catalog for the new language:

   ```sh
   msginit --no-translator -l fr -i po/nautilus-create-file.pot -o po/fr.po
   ```

   Alternatively, copy `po/nautilus-create-file.pot` to `po/<lang>.po` and set
   `"Language: <lang>\n"` in the header.

2. Translate the `msgstr` entries, e.g. with Poedit or Gtranslator.
3. Add `<lang>` to `po/LINGUAS`.
4. Check the result:

   ```sh
   msgfmt --check -o /dev/null po/<lang>.po
   ```

5. Install and try it in Nautilus. `install.sh` installs every catalog, so the
   `LANGUAGE` variable only matters for Nautilus itself:

   ```sh
   bash install.sh
   nautilus -q
   LANGUAGE=<lang> nautilus
   ```

Pull requests with new translations are welcome. If you would rather use a web
interface, a Weblate project can be connected to this repository.

When strings change, regenerate the template and merge it into the catalogs:

```sh
xgettext --from-code=UTF-8 -L Python -k_ \
    --package-name=nautilus-create-file --package-version=1.0.0 \
    -o po/nautilus-create-file.pot nautilus-create-file.py
msgmerge --update po/de.po po/nautilus-create-file.pot
```

## Development

The checks below use GNU gettext. On Debian/Ubuntu: `sudo apt install gettext`.

```sh
python3 -m py_compile nautilus-create-file.py tests/*.py
python3 -m unittest discover -s tests -v

for po in po/*.po; do
    msgfmt --check -o /dev/null "$po"
    msgcmp "$po" po/nautilus-create-file.pot
done

xgettext --from-code=UTF-8 -L Python -k_ \
    --package-name=nautilus-create-file --package-version=1.0.0 \
    -o /tmp/current.pot nautilus-create-file.py
msgcmp --use-untranslated /tmp/current.pot po/nautilus-create-file.pot
msgcmp --use-untranslated po/nautilus-create-file.pot /tmp/current.pot
```

With Meson the usual gettext targets are available:

```sh
meson setup build --prefix="$HOME/.local"
meson compile -C build nautilus-create-file-pot
meson compile -C build nautilus-create-file-update-po
meson install -C build
```

CI checks the syntax, runs the unit tests, verifies that every message is
translated and that the template matches the source strings.

## Known limitations

- The newly created file is not selected afterwards (the Nautilus extension API has no hook for this).

## License

GPL-3.0-or-later, see [LICENSE](LICENSE).
