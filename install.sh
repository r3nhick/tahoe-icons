#!/usr/bin/env bash
# Installs Tahoe Default / Tahoe White / Tahoe Blue into ~/.icons
set -euo pipefail
cd "$(dirname "$0")"
DEST="${HOME}/.icons"
mkdir -p "$DEST"


for theme in Tahoe-Default Tahoe-White Tahoe-Blue; do
  echo "Installing $theme"
  rm -rf "${DEST:?}/$theme"
  cp -a "$theme" "$DEST/"
  command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -f -q "$DEST/$theme" || true
done

echo
echo "Done. Pick one with:"
echo "  gsettings set org.gnome.desktop.interface icon-theme 'Tahoe-Default'   # or Tahoe-White / Tahoe-Blue"
