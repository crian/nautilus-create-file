import gettext
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PO_DIR = ROOT / "po"
POT = PO_DIR / "nautilus-create-file.pot"
MSGFMT = shutil.which("msgfmt")
MSGCMP = shutil.which("msgcmp")

# Keep this in sync with the string in nautilus-create-file.py
PLACEHOLDER_MSGID = "“{name}” already exists."


def catalogs():
    return sorted(PO_DIR.glob("*.po"))


class CatalogTest(unittest.TestCase):
    def test_template_exists(self):
        self.assertTrue(POT.is_file(), f"{POT} is missing")

    def test_linguas_lists_every_catalog(self):
        linguas = set((PO_DIR / "LINGUAS").read_text(encoding="utf-8").split())
        self.assertTrue(catalogs(), "no translations found in po/")
        self.assertEqual({po.stem for po in catalogs()}, linguas)

    @unittest.skipUnless(MSGFMT, "msgfmt (gettext) is required")
    def test_catalogs_compile_and_load(self):
        for po in catalogs():
            with self.subTest(catalog=po.name):
                with tempfile.TemporaryDirectory() as tmp:
                    mo = Path(tmp) / f"{po.stem}.mo"
                    subprocess.run(
                        [MSGFMT, "--check", "-o", str(mo), str(po)],
                        check=True,
                        capture_output=True,
                    )
                    with mo.open("rb") as stream:
                        translations = gettext.GNUTranslations(stream)
                self.assertEqual(translations.info().get("language"), po.stem)
                message = translations.gettext(PLACEHOLDER_MSGID)
                self.assertIn("{name}", message)
                message.format(name="example.txt")  # must not raise

    @unittest.skipUnless(MSGCMP, "msgcmp (gettext) is required")
    def test_catalogs_are_complete(self):
        for po in catalogs():
            with self.subTest(catalog=po.name):
                result = subprocess.run(
                    [MSGCMP, str(po), str(POT)],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
