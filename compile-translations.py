#!/usr/bin/env python3
"""Compile po/*.po into locale/<lang>/LC_MESSAGES/nautilus-create-file.mo.

Pure Python, so no gettext tools (msgfmt) are required.
Usage: python3 compile-translations.py
"""
import ast
import os
import struct
import sys

DOMAIN = "nautilus-create-file"
ROOT = os.path.dirname(os.path.abspath(__file__))


def parse_po(path):
    messages, msgid, msgstr, section, fuzzy = {}, None, None, None, False

    def flush():
        if msgid is not None and msgstr is not None and not fuzzy:
            if msgstr or msgid == "":
                messages[msgid] = msgstr

    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if line.startswith("#,") and "fuzzy" in line:
                flush()
                msgid, msgstr, section, fuzzy = None, None, None, True
                continue
            if line.startswith("#") or not line:
                if not line:
                    flush()
                    msgid, msgstr, section, fuzzy = None, None, None, False
                continue
            if line.startswith("msgid "):
                flush()
                msgid, msgstr, section = ast.literal_eval(line[6:]), None, "id"
            elif line.startswith("msgstr "):
                msgstr, section = ast.literal_eval(line[7:]), "str"
            elif line.startswith('"'):
                text = ast.literal_eval(line)
                if section == "id":
                    msgid += text
                elif section == "str":
                    msgstr += text
    flush()
    return messages


def write_mo(messages, path):
    keys = sorted(messages)
    ids, strs, offsets = b"", b"", []
    for k in keys:
        kb, vb = k.encode("utf-8"), messages[k].encode("utf-8")
        offsets.append((len(ids), len(kb), len(strs), len(vb)))
        ids += kb + b"\0"
        strs += vb + b"\0"
    n = len(keys)
    keystart = 7 * 4 + 16 * n
    valuestart = keystart + len(ids)
    koffsets, voffsets = [], []
    for o1, l1, o2, l2 in offsets:
        koffsets += [l1, o1 + keystart]
        voffsets += [l2, o2 + valuestart]
    out = struct.pack("Iiiiiii", 0x950412DE, 0, n, 7 * 4, 7 * 4 + n * 8, 0, 0)
    out += struct.pack(f"{len(koffsets)}i", *koffsets)
    out += struct.pack(f"{len(voffsets)}i", *voffsets)
    out += ids + strs
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(out)


def main():
    po_dir = os.path.join(ROOT, "po")
    found = False
    for name in sorted(os.listdir(po_dir)):
        if not name.endswith(".po"):
            continue
        found = True
        lang = name[:-3]
        target = os.path.join(ROOT, "locale", lang, "LC_MESSAGES", f"{DOMAIN}.mo")
        write_mo(parse_po(os.path.join(po_dir, name)), target)
        print(f"{name} -> {os.path.relpath(target, ROOT)}")
    if not found:
        sys.exit("No .po files found in po/")


if __name__ == "__main__":
    main()
