#!/usr/bin/env bash
# Per-user install without meson/gettext tools.
# Usage: ./install.sh [uninstall]
set -euo pipefail

cd "$(dirname "$0")"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
EXT_DIR="$DATA/nautilus-python/extensions"
DOMAIN="nautilus-create-file"

if [[ "${1:-}" == "uninstall" ]]; then
    rm -f "$EXT_DIR/nautilus-create-file.py"
    find "$DATA/locale" -name "$DOMAIN.mo" -delete 2>/dev/null || true
    echo "Removed. Restart Nautilus with: nautilus -q"
    exit 0
fi

python3 compile-translations.py >/dev/null

mkdir -p "$EXT_DIR"
install -m 644 nautilus-create-file.py "$EXT_DIR/nautilus-create-file.py"

for mo in locale/*/LC_MESSAGES/$DOMAIN.mo; do
    lang="$(basename "$(dirname "$(dirname "$mo")")")"
    install -Dm 644 "$mo" "$DATA/locale/$lang/LC_MESSAGES/$DOMAIN.mo"
done

echo "Installed. Restart Nautilus with: nautilus -q"
