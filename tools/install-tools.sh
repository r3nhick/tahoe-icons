#!/usr/bin/env bash
# Installs `tahoe-icons` and a user service that runs it whenever an app is installed (pacman, Flatpak, ~/.local).
set -e
here=$(cd "$(dirname "$0")" && pwd)
dest="$HOME/.local/share/tahoe-icons"
python3 -c 'import numpy, PIL' 2>/dev/null || { echo "Needs: sudo pacman -S --needed python-numpy python-pillow librsvg"; exit 1; }
command -v rsvg-convert >/dev/null || { echo "Needs: sudo pacman -S --needed librsvg"; exit 1; }
mkdir -p "$dest" "$HOME/.local/bin" "$HOME/.config/systemd/user"
cp "$here/tahoe-icons" "$here/tahoe_lib.py" "$dest/"
chmod +x "$dest/tahoe-icons"
ln -sf "$dest/tahoe-icons" "$HOME/.local/bin/tahoe-icons"
cp "$here/systemd/tahoe-icons.service" "$here/systemd/tahoe-icons.path" "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable --now tahoe-icons.path
"$HOME/.local/bin/tahoe-icons" update
echo "Done. New apps get Tahoe icons automatically; run 'tahoe-icons list' to see what is missing."
