#!/usr/bin/env bash
# Per-user install. Translations are compiled with msgfmt (GNU gettext).
# Usage: ./install.sh [uninstall]
set -euo pipefail
shopt -s nullglob

cd "$(dirname "$0")"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
EXT_DIR="$DATA/nautilus-python/extensions"
DOMAIN="nautilus-create-file"

if [[ "${1:-}" == "uninstall" ]]; then
    rm -f "$EXT_DIR/nautilus-create-file.py"
    rm -f "$EXT_DIR"/__pycache__/nautilus-create-file.*.pyc
    rmdir "$EXT_DIR/__pycache__" 2>/dev/null || true
    while IFS= read -r mo; do
        rm -f "$mo"
        rmdir "$(dirname "$mo")" 2>/dev/null || true
        rmdir "$(dirname "$(dirname "$mo")")" 2>/dev/null || true
    done < <(find "$DATA/locale" -name "$DOMAIN.mo" 2>/dev/null)
    echo "Removed. Restart Nautilus with: nautilus -q"
    exit 0
fi

mkdir -p "$EXT_DIR"
install -m 644 nautilus-create-file.py "$EXT_DIR/nautilus-create-file.py"

if command -v msgfmt >/dev/null 2>&1; then
    for po in po/*.po; do
        lang="$(basename "$po" .po)"
        dir="$DATA/locale/$lang/LC_MESSAGES"
        mkdir -p "$dir"
        msgfmt --check -o "$dir/$DOMAIN.mo" "$po"
    done
else
    echo "Warning: msgfmt not found, installing without translations." >&2
    echo "Install gettext and run again to include them." >&2
fi

echo "Installed. Restart Nautilus with: nautilus -q"
