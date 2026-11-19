# Tahoe Icons

Three macOS Tahoe–style icon themes for Linux (GNOME), built on top of MacTahoe / WhiteSur.

| Theme | Look |
|---|---|
| **Tahoe Default** | Colourful macOS Tahoe app icons with WhiteSur folders |
| **Tahoe White** | Dark monochrome: dark glass tiles, white glyphs (like macOS Tahoe's dark "tinted" icons) |
| **Tahoe Blue** | Dark monochrome with slate-blue `#6f8396` glyphs |

## Screenshots

**Tahoe Default**

![Tahoe Default](assets/default.png)

**Tahoe White**

![Tahoe White](assets/white.png)

**Tahoe Blue**

![Tahoe Blue](assets/blue.png)

## Install

```bash
git clone git@github.com:r3nhick/tahoe-icons.git
cd tahoe-icons
./install.sh
gsettings set org.gnome.desktop.interface icon-theme 'Tahoe-Default'   # or Tahoe-White / Tahoe-Blue
```

Log out and back in (Wayland) so GNOME Shell and the dock pick up the new icons.

### Requirements

The themes inherit every icon they don't define from **MacOS-Like-Dark** and **MacOS-Like-Dark-AdwFolders**
(a MacTahoe-based theme). Install those into `~/.icons` as well, otherwise some icons fall back to hicolor/Adwaita.

## What's inside

- **Tahoe Default** – app icons and folder icons; custom icons for Claude, Discord, Firefox, GitHub, Liner,
  Motrix, Obsidian, Spotify and Telegram.
- **Tahoe White / Tahoe Blue** – ~1,400 app icons plus folders and trash, recoloured to dark monochrome and
  pre-rendered as PNG at 16, 24, 32, 48, 64, 96, 128 and 256 px, so they stay pixel-sharp in the dock and
  don't use SVG filters (which crash GTK 4.24's SVG renderer). All app-id aliases
  (`org.telegram.desktop`, `com.spotify.Client`, …) are kept as symlinks.

## Credits & licence

Based on [MacTahoe](https://github.com/vinceliuice/MacTahoe-icon-theme) and
[WhiteSur](https://github.com/vinceliuice/WhiteSur-icon-theme) icon themes by Vince Liuice.
Licensed under the GNU GPL v3 — see [LICENSE](LICENSE).
