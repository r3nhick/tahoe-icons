#!/usr/bin/env bash
# Finds installed apps whose icon is missing from the Tahoe themes and copies their original icons
# into ~/tahoe-missing (one file per icon name + list.txt), so they can be converted.
set -u
OUT="$HOME/tahoe-missing"; mkdir -p "$OUT"; : > "$OUT/list.txt"
CHECK="$HOME/.icons/Tahoe-White/png/apps/64"
APPDIRS=(/usr/share/applications /usr/local/share/applications /var/lib/flatpak/exports/share/applications
         "$HOME/.local/share/flatpak/exports/share/applications" "$HOME/.local/share/applications")
ICONDIRS=(/var/lib/flatpak/exports/share/icons/hicolor "$HOME/.local/share/flatpak/exports/share/icons/hicolor"
          "$HOME/.local/share/icons/hicolor" /usr/local/share/icons/hicolor /usr/share/icons/hicolor)

find_icon() {  # best source for an icon name: scalable SVG, else the largest PNG, else pixmaps
  local n="$1" d s
  for d in "${ICONDIRS[@]}"; do [ -f "$d/scalable/apps/$n.svg" ] && { echo "$d/scalable/apps/$n.svg"; return; }; done
  for s in 1024x1024 512x512 256x256 192x192 128x128 96x96 64x64 48x48; do
    for d in "${ICONDIRS[@]}"; do [ -f "$d/$s/apps/$n.png" ] && { echo "$d/$s/apps/$n.png"; return; }; done
  done
  for e in svg png xpm; do [ -f "/usr/share/pixmaps/$n.$e" ] && { echo "/usr/share/pixmaps/$n.$e"; return; }; done
}

for dir in "${APPDIRS[@]}"; do
  [ -d "$dir" ] || continue
  for f in "$dir"/*.desktop; do
    [ -f "$f" ] || continue
    grep -qE '^NoDisplay=true' "$f" && continue
    icon=$(grep -m1 '^Icon=' "$f" | cut -d= -f2-); name=$(grep -m1 '^Name=' "$f" | cut -d= -f2-)
    [ -n "$icon" ] || continue
    if [[ "$icon" == /* ]]; then src="$icon"; key=$(basename "${f%.desktop}")
    else [ -e "$CHECK/$icon.png" ] && continue; src=$(find_icon "$icon"); key="$icon"; fi
    grep -q "^$key|" "$OUT/list.txt" && continue
    if [ -n "$src" ] && [ -f "$src" ]; then
      cp -L "$src" "$OUT/$key.${src##*.}"; echo "$key|$name|$src" >> "$OUT/list.txt"
    else
      echo "$key|$name|NOT FOUND" >> "$OUT/list.txt"
    fi
  done
done
echo "Missing: $(wc -l < "$OUT/list.txt") — copied to $OUT"
cat "$OUT/list.txt"
