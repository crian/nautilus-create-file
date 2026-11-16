import gettext
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "compile_translations", ROOT / "compile-translations.py"
)
compile_translations = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(compile_translations)


class ParsePoTest(unittest.TestCase):
    def parse(self, content):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".po", encoding="utf-8", delete=False
        ) as f:
            f.write(content)
            path = f.name
        try:
            return compile_translations.parse_po(path)
        finally:
            os.unlink(path)

    def test_simple_messages(self):
        messages = self.parse(
            'msgid ""\n'
            'msgstr ""\n'
            '"Language: de\\n"\n'
            "\n"
            'msgid "Hello"\n'
            'msgstr "Hallo"\n'
        )
        self.assertEqual(messages["Hello"], "Hallo")

    def test_multiline_message(self):
        messages = self.parse(
            'msgid ""\n'
            'msgstr ""\n'
            "\n"
            'msgid ""\n'
            '"multi"\n'
            '"line"\n'
            'msgstr ""\n'
            '"mehr"\n'
            '"zeilig"\n'
        )
        self.assertEqual(messages["multiline"], "mehrzeilig")

    def test_fuzzy_messages_are_skipped(self):
        messages = self.parse(
            'msgid ""\n'
            'msgstr ""\n'
            "\n"
            "#, fuzzy\n"
            'msgid "Fuzzy"\n'
            'msgstr "Unsicher"\n'
            "\n"
            'msgid "Done"\n'
            'msgstr "Fertig"\n'
        )
        self.assertNotIn("Fuzzy", messages)
        self.assertEqual(messages["Done"], "Fertig")

    def test_untranslated_messages_are_skipped(self):
        messages = self.parse(
            'msgid ""\n'
            'msgstr ""\n'
            "\n"
            'msgid "Untranslated"\n'
            'msgstr ""\n'
        )
        self.assertNotIn("Untranslated", messages)


class WriteMoTest(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            po = Path(tmp) / "test.po"
            mo = Path(tmp) / "test.mo"
            po.write_text(
                'msgid ""\n'
                'msgstr ""\n'
                '"Language: de\\n"\n'
                "\n"
                'msgid "Hello"\n'
                'msgstr "Hallo"\n',
                encoding="utf-8",
            )
            messages = compile_translations.parse_po(str(po))
            compile_translations.write_mo(messages, str(mo))
            with mo.open("rb") as f:
                translations = gettext.GNUTranslations(f)
            self.assertEqual(translations.gettext("Hello"), "Hallo")


if __name__ == "__main__":
    unittest.main()
