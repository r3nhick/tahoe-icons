"""Tahoe Default -> dark-mode tiles (like macOS Tahoe's dark app icons).

For every squircle app icon: the tile colour is modelled from its edge ring (a smooth 2-D fit, so gradients count
as background too), everything that differs from it is the glyph and is kept; the tile itself becomes dark grey.
A white/grey glyph on a saturated tile takes the tile's colour (white note on red -> red note on dark).
Icons whose tile is already dark, and free-form icons with no tile, are left as they are.
Output: crisp PNGs for every size, rendered once at 512 px and downsampled.
"""
import os, sys, subprocess, io, colorsys, re, base64
import numpy as np
from PIL import Image

N = 512
SIZES = [16, 24, 32, 48, 64, 96, 128, 256, 512]


def sq(n):
    s = n / 64.0
    yy, xx = np.mgrid[0:n, 0:n] + 0.5
    x0, y0, w, r = 4 * s, 3.969 * s, 56.002 * s, 13.002 * s
    cx = np.clip(xx, x0 + r, x0 + w - r); cy = np.clip(yy, y0 + r, y0 + w - r)
    d = np.hypot(xx - cx, yy - cy) - r
    inside = (xx >= x0) & (xx <= x0 + w) & (yy >= y0) & (yy <= y0 + w) & (d <= 0)
    return inside, d, xx / n, yy / n


MASK, D, X, Y = sq(N)
RING = MASK & (D > -34) & (D < -10)
INNER = MASK & (D < -6)

# dark tile (macOS dark icon grey, lit from above) + a faint rim
TOP, BOT = np.array([0.235, 0.235, 0.25]), np.array([0.11, 0.11, 0.12])
TT = np.clip((Y - 0.06) / 0.88, 0, 1)[..., None]
TILE = TOP * (1 - TT) + BOT * TT
RIM = ((D > -3.5) & (D <= 0))
TILE = np.where(RIM[..., None], TILE + 0.07 * (1 - TT), TILE)


IMG = re.compile(r'<image\b[^>]*?(?:/>|>.*?</image>)', re.S)


def strip_glows(svg):
    """Drop the low-resolution raster layers (blurred glows/shadows under the logo) when the icon has
    vector artwork of its own; keep rasters that are the picture itself."""
    has_vector = re.search(r'<(path|rect|circle|ellipse|polygon|polyline)\b', svg) is not None
    def repl(m):
        t = m.group(0)
        if 'tahoeShadow' in t:
            return t
        h = re.search(r'href="data:image/(?:png|jpe?g);base64,([^"]+)"', t)
        w = re.search(r'\bwidth="([\d.]+)', t)
        if not h or not w or not has_vector:
            return t
        try:
            im = Image.open(io.BytesIO(base64.b64decode(re.sub(r'\s', '', h.group(1)))))
        except Exception:
            return t
        density = im.size[0] / max(float(w.group(1)), 1e-3)
        a = np.asarray(im.convert('RGBA'))[..., 3].astype(np.float32) / 255
        vis = a > 0.05
        soft = ((a > 0.05) & (a < 0.85)).sum() / max(vis.sum(), 1)
        # a blurred glow/shadow: mostly semi-transparent. Pixel art and real pictures have hard edges.
        return '' if (soft > 0.45 and density < 6.0) else t
    svg = IMG.sub(repl, svg)
    if has_vector:
        blur_ids = set()
        for m in re.finditer(r'<filter\b[^>]*\bid="([^"]+)"[^>]*>(.*?)</filter>', svg, re.S):
            sd = re.search(r'stdDeviation="([\d.]+)', m.group(2))
            if 'feGaussianBlur' in m.group(2) and sd and float(sd.group(1)) >= 0.6 and 'feColorMatrix' not in m.group(2):
                blur_ids.add(m.group(1))
        for i in blur_ids:
            # self-closing shapes drawn through the blur (glows, soft shadows)
            svg = re.sub(r'<(path|rect|circle|ellipse|use|polygon)\b[^>]*filter="url\(#' + re.escape(i) + r'\)"[^>]*/>', '', svg)
    return svg


def render(path):
    svg = open(path, encoding='utf-8', errors='replace').read()
    svg = strip_glows(svg)
    p = subprocess.run(['rsvg-convert', '-w', str(N), '-h', str(N)], input=svg.encode(), capture_output=True, timeout=60)
    if p.returncode:
        return None
    return np.asarray(Image.open(io.BytesIO(p.stdout)).convert('RGBA')).astype(np.float32) / 255


def basis(x, y):
    return np.stack([np.ones_like(x), x, y, x * y, x * x, y * y], -1)


def lum(c):
    return c[..., 0] * .2126 + c[..., 1] * .7152 + c[..., 2] * .0722


def normalize(a):
    """An icon drawn as a squircle of another size/inset (a whole raster app icon, say): scale it onto Tahoe's tile."""
    al = a[..., 3]
    ys, xs = np.where(al > 0.5)
    if len(xs) == 0:
        return None
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    w, h = x1 - x0, y1 - y0
    if not (0.85 < w / h < 1.18) or w < N * 0.5:
        return None
    if (al[y0:y1, x0:x1] > 0.5).mean() < 0.86:   # not a filled tile
        return None
    side = int(round(56.002 / 64 * N))
    crop = Image.fromarray((a[y0:y1, x0:x1] * 255).astype(np.uint8), 'RGBA').resize((side, side), Image.LANCZOS)
    canvas = Image.new('RGBA', (N, N), (0, 0, 0, 0))
    canvas.paste(crop, (int(round(4 / 64 * N)), int(round(3.969 / 64 * N))))
    b = np.asarray(canvas).astype(np.float32) / 255
    # clip to Tahoe's squircle so the corners match
    b[..., 3] *= MASK
    return b


def darken(a):
    """Returns (rgba, mode)."""
    al = a[..., 3]
    if (al[INNER] > 0.9).mean() < 0.97:
        b = normalize(a)
        if b is None or (b[..., 3][INNER] > 0.9).mean() < 0.97:
            return a, 'free'
        a, al = b, b[..., 3]
    rgb = a[..., :3]
    ring = RING & (al > 0.9)
    if rgb[ring].max(-1).mean() < 0.3:
        bright = (rgb.max(-1) > 0.5) & MASK
        prof = [(d, bright[(D <= d) & (D > d - 3) & MASK].mean()) for d in range(-1, -60, -3)]
        if max(v for d, v in prof[:4]) > 0.6:
            cut = next((d for d, v in prof if d < -6 and v < 0.2), None)
            if cut is not None:
                out = a.copy()
                band = (MASK & (D > cut))[..., None]
                out[..., :3] = np.where(band, TILE, rgb)
                return out, 'dark-reframed'
        return a, 'dark'
    # robust smooth fit of the tile colour
    B = basis(X[ring], Y[ring]); C = rgb[ring]
    keep = np.ones(len(C), bool)
    for _ in range(3):
        coef, *_ = np.linalg.lstsq(B[keep], C[keep], rcond=None)
        res = np.linalg.norm(B @ coef - C, axis=1)
        keep = res < max(0.06, np.percentile(res, 70) * 2.5)
    bg = basis(X, Y) @ coef
    dist = np.linalg.norm(rgb - bg, axis=-1)
    # icons with a frame: the ring is the frame, the real background is the big flat area inside it
    q = np.round(rgb[INNER] * 15).astype(int)
    key = q[:, 0] * 256 + q[:, 1] * 16 + q[:, 2]
    vals, counts = np.unique(key, return_counts=True)
    dom = vals[counts.argmax()]
    dom_rgb = rgb[INNER][key == dom].mean(0)
    d2 = np.linalg.norm(rgb - dom_rgb, axis=-1)
    if (d2[INNER] < 0.07).mean() > (dist[INNER] < 0.07).mean() + 0.15 and dom_rgb.max() > 0.3:
        dist = d2
        C = rgb[INNER][key == dom]; keep = np.ones(len(C), bool)
    f = np.clip((dist - 0.07) / 0.13, 0, 1)
    f = np.where(D > -11, 0, f)         # the old tile's own rim/edge shading
    f *= (al > 0)
    prof = [(d, f[(D <= d) & (D > d - 3) & MASK].mean()) for d in range(-11, -90, -3)]
    if prof[0][1] > 0.6:
        cut = next((d for d, v in prof if v < 0.3), None)
        if cut is not None and cut > -80:
            f = np.where(D > cut, 0, f)

    bgm = np.clip(C[keep].mean(0), 0, 1)
    h, s, v = colorsys.rgb_to_hsv(*bgm)
    glyph = rgb.copy()
    gsat = (rgb.max(-1) - rgb.min(-1)) / (rgb.max(-1) + 1e-6)
    gl = lum(rgb)
    if s > 0.35:
        # neutral (white/grey) glyph parts on a coloured tile take the tile's colour, shaded by their lightness
        tint = np.array(colorsys.hsv_to_rgb(h, min(1, s * 1.05), max(v, 0.92)))
        neutral = np.clip((0.3 - gsat) / 0.2, 0, 1)[..., None] * (gl > 0.45)[..., None]
        glyph = glyph * (1 - neutral) + (tint * (0.55 + 0.45 * gl[..., None])) * neutral
    out = a.copy()
    inside = MASK[..., None]
    mode = 'dark-tile'
    if f[INNER].mean() > 0.55:
        # full-bleed artwork (a map, a photo): no tile to swap, so dim the whole picture instead —
        # unless it is already darkish; darkened by multiplying, so its colours stay saturated
        if rgb[INNER].max(-1).mean() < 0.4:
            return a, 'dark'
        comp = rgb * 0.46
        comp = np.where(RIM[..., None], TILE, comp)
        mode = 'dimmed'
    else:
        comp = TILE * (1 - f[..., None]) + glyph * f[..., None]
    out[..., :3] = np.where(inside, comp, rgb)
    # the anti-aliased fringe just outside the old tile takes the dark edge, not the old colour
    fringe = ((D > 0) & (D < 3))[..., None]
    out[..., :3] = np.where(fringe, BOT, out[..., :3])
    out[..., 3] = np.where(MASK, np.maximum(al, MASK.astype(np.float32)), al)
    return out, mode



TILE_RECT = re.compile(r'<rect\b(?=[^>]*\bwidth="56(?:\.0+2?)?")(?=[^>]*\bheight="56(?:\.0+2?)?")(?=[^>]*\bx="4")[^>]*?(/?)>')
DARK_DEFS = ('<linearGradient id="tahoeDarkTile" x1="0" x2="0" y1="4" y2="60" gradientUnits="userSpaceOnUse">'
             '<stop offset="0" stop-color="#3c3c40"/><stop offset="1" stop-color="#1c1c1f"/></linearGradient>')


def dark_tile_svg(svg):
    """Paints MacTahoe's tile rect(s) dark; None if the icon has no such rect."""
    if not TILE_RECT.search(svg):
        return None
    def repl(m):
        t = m.group(0)
        t = re.sub(r'\sfill="[^"]*"', '', t)
        t = re.sub(r'\sfill-opacity="[^"]*"', '', t)
        t = re.sub(r'\sstyle="[^"]*"', '', t)
        t = re.sub(r'\sopacity="[^"]*"', '', t)
        return t.replace('<rect', '<rect fill="url(#tahoeDarkTile)"', 1)
    out = TILE_RECT.sub(repl, svg)
    if '<defs>' in out:
        out = out.replace('<defs>', '<defs>' + DARK_DEFS, 1)
    else:
        out = re.sub(r'(<svg\b[^>]*>)', r'\1<defs>' + DARK_DEFS + '</defs>', out, count=1)
    return out


def rsvg(svg):
    p = subprocess.run(['rsvg-convert', '-w', str(N), '-h', str(N)], input=svg.encode(), capture_output=True, timeout=60)
    if p.returncode:
        return None
    return np.asarray(Image.open(io.BytesIO(p.stdout)).convert('RGBA')).astype(np.float32) / 255


EDGE = MASK & (D < -11) & (D > -60)


def leftover(out):
    """Share of the tile's edge band still bright or vivid after processing (the old tile not found)."""
    c = out[..., :3][EDGE]
    return (c.max(-1) > 0.42).mean()


def process(path):
    """Returns (rgba, mode)."""
    out, mode, a0 = _process(path)
    if out is None or mode in ('free', 'render-failed') or a0 is None:
        return out, mode
    if leftover(out) > 0.3 or (mode == 'dark-reframed' and (out[..., :3][INNER].max(-1) > 0.75).mean() > 0.4):
        b = a0.copy()
        b[..., :3] = np.where(MASK[..., None], a0[..., :3] * 0.46, a0[..., :3])
        return b, 'fallback-dimmed'
    return out, mode


def _process(path):
    svg = strip_glows(open(path, encoding='utf-8', errors='replace').read())
    a0 = rsvg(svg)
    if a0 is None:
        return None, 'render-failed', None
    dsvg = dark_tile_svg(svg)
    if dsvg is not None and (a0[..., 3][INNER] > 0.9).mean() >= 0.97:
        ring = RING & (a0[..., 3] > 0.9)
        if a0[..., :3][ring].max(-1).mean() < 0.3:
            return (*darken(a0), a0)     # already dark: reuse the frame handling
        a1 = rsvg(dsvg)
        if a1 is not None and a1[..., :3][ring].max(-1).mean() < 0.3:
            rgb0, rgb1 = a0[..., :3], a1[..., :3]
            f = np.clip((np.linalg.norm(rgb1 - TILE, axis=-1) - 0.06) / 0.1, 0, 1) * MASK
            out = a1.copy()
            if f[INNER].mean() > 0.55:
                out[..., :3] = np.where(MASK[..., None], rgb1 * 0.46, rgb1)
                return out, 'svg-dimmed', a0
            bgm = np.clip(rgb0[ring].mean(0), 0, 1)
            h, s_, v = colorsys.rgb_to_hsv(*bgm)
            if s_ > 0.35:
                gsat = (rgb1.max(-1) - rgb1.min(-1)) / (rgb1.max(-1) + 1e-6)
                gl = lum(rgb1)
                tint = np.array(colorsys.hsv_to_rgb(h, min(1, s_ * 1.05), max(v, 0.92)))
                neutral = (np.clip((0.3 - gsat) / 0.2, 0, 1) * (gl > 0.45) * f)[..., None]
                out[..., :3] = rgb1 * (1 - neutral) + (tint * (0.55 + 0.45 * gl[..., None])) * neutral
            return out, 'svg-tile', a0
    r, m = darken(a0)
    if m in ('dark-tile', 'dimmed', 'dark-reframed', 'dark'):
        # darken() may have normalised the icon onto the standard tile; compare against that
        pass
    return r, m, (normalize(a0) if (a0[..., 3][INNER] > 0.9).mean() < 0.97 and normalize(a0) is not None else a0)


def save_all(rgba, name, outroot):
    im = Image.fromarray((np.clip(rgba, 0, 1) * 255).astype(np.uint8), 'RGBA')
    for s in SIZES:
        d = f'{outroot}/{s}'
        os.makedirs(d, exist_ok=True)
        (im if s == N else im.resize((s, s), Image.LANCZOS)).save(f'{d}/{name}.png')


def main(src, outroot, names=None, workers=(0, 1)):
    k, n = workers
    files = sorted(f for f in os.listdir(src) if f.endswith('.svg') and not os.path.islink(f'{src}/{f}'))
    if names:
        files = [f for f in files if f[:-4] in names]
    files = files[k::n]
    modes = {}
    for f in files:
        out, mode = process(f'{src}/{f}')
        if out is None:
            modes[f] = mode
            continue
        modes[f] = mode
        save_all(out, f[:-4], outroot)
    return modes




# ---------------- monochrome (Tahoe White / Blue / Red / Green) ----------------

def glyph_mask(a):
    """Glyph of a processed (dark) icon: what clearly differs from its own tile."""
    rgb, al = a[..., :3], a[..., 3]
    if (al[INNER] > 0.9).mean() < 0.97:
        ys, xs = np.where(al > 0.05)
        if len(xs) == 0:
            return None, None
        x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        side = int(N * 36 / 64); sc = side / max(x1 - x0, y1 - y0)
        im = Image.fromarray((a[y0:y1, x0:x1] * 255).astype(np.uint8), 'RGBA')
        im = im.resize((max(1, int((x1 - x0) * sc)), max(1, int((y1 - y0) * sc))), Image.LANCZOS)
        cv = Image.new('RGBA', (N, N)); cv.paste(im, ((N - im.size[0]) // 2, (N - im.size[1]) // 2))
        b = np.asarray(cv).astype(np.float32) / 255
        return b[..., 3], b[..., :3]
    ring = RING & (al > 0.9)
    B = basis(X[ring], Y[ring]); C = rgb[ring]; keep = np.ones(len(C), bool)
    for _ in range(3):
        coef, *_ = np.linalg.lstsq(B[keep], C[keep], rcond=None)
        res = np.linalg.norm(B @ coef - C, axis=1)
        keep = res < max(0.05, np.percentile(res, 70) * 2.5)
    dist = np.linalg.norm(rgb - basis(X, Y) @ coef, axis=-1)
    f = np.clip((dist - 0.10) / 0.08, 0, 1)
    f = np.where(D > -22, 0, f) * MASK
    prof = [(d, f[(D <= d) & (D > d - 3) & MASK].mean()) for d in range(-22, -90, -3)]
    if prof[0][1] > 0.5:
        cut = next((d for d, v in prof if v < 0.25), None)
        if cut is not None and cut > -80:
            f = np.where(D > cut, 0, f)
    return f, rgb


def symbolic_mask(path):
    side = int(N * 34 / 64)
    p = subprocess.run(['rsvg-convert', '-w', str(side), '-h', str(side), path], capture_output=True)
    if p.returncode:
        return None
    im = Image.open(io.BytesIO(p.stdout)).convert('RGBA')
    cv = Image.new('RGBA', (N, N)); cv.paste(im, ((N - side) // 2, (N - side) // 2 + 1))
    return np.asarray(cv).astype(np.float32)[..., 3] / 255


def compose(f, rgb, colour):
    tint = np.array([int(colour[i:i + 2], 16) for i in (1, 3, 5)], np.float32) / 255
    L = lum(rgb); sel = f > 0.5
    lo, hi = (np.percentile(L[sel], 5), np.percentile(L[sel], 95)) if sel.sum() > 50 else (0, 0)
    shade = np.ones_like(L) if hi - lo < 0.02 else 0.62 + 0.38 * np.clip((L - lo) / max(hi - lo, 1e-3), 0, 1)
    out = np.zeros((N, N, 4), np.float32)
    out[..., :3] = TILE * (1 - f[..., None]) + (tint * shade[..., None]) * f[..., None]
    out[..., 3] = MASK
    return out


def wrap_free(a):
    """An app icon of any shape (most hicolor icons) placed on Tahoe's dark tile, like macOS does."""
    al = a[..., 3]
    ys, xs = np.where(al > 0.05)
    out = np.zeros((N, N, 4), np.float32)
    out[..., :3] = TILE; out[..., 3] = MASK
    if len(xs) == 0:
        return out
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    side = int(N * 40 / 64); sc = side / max(x1 - x0, y1 - y0)
    im = Image.fromarray((a[y0:y1, x0:x1] * 255).astype(np.uint8), 'RGBA')
    im = im.resize((max(1, int((x1 - x0) * sc)), max(1, int((y1 - y0) * sc))), Image.LANCZOS)
    cv = Image.new('RGBA', (N, N)); cv.paste(im, ((N - im.size[0]) // 2, (N - im.size[1]) // 2))
    g = np.asarray(cv).astype(np.float32) / 255
    out[..., :3] = out[..., :3] * (1 - g[..., 3:]) + g[..., :3] * g[..., 3:]
    return out


# ---------------- Tahoe Blue/Red/Green tinting of "hazy" icons, and Tahoe Black ----------------

def tinted(a, col):
    """Grey version of a processed icon whose highlights take the theme colour (for icons whose glyph is not a clean shape)."""
    t = np.array([int(col[i:i + 2], 16) for i in (1, 3, 5)], np.float32) / 255
    L = lum(a[..., :3])[..., None]
    grey = np.repeat(L ** 1.2, 3, -1)
    colour = t * np.clip(L / 0.68, 0, 1.15)
    w = np.clip((L - 0.24) / 0.32, 0, 1)
    out = a.copy(); out[..., :3] = np.clip(grey * (1 - w) + colour * w, 0, 1)
    return out


def greyed(a):
    """Tahoe Black: the processed icon in plain greys."""
    L = lum(a[..., :3])[..., None]
    out = a.copy(); out[..., :3] = np.clip(np.repeat(L ** 1.2, 3, -1), 0, 1)
    return out


def mono_set(dark, glyph_src, wrapped, colours):
    """{'Tahoe-White': rgba, ...} from the dark Tahoe Default icon.
    glyph_src: the picture the glyph is cut from (the original for icons placed on the tile, else the dark icon itself)."""
    gm, grgb = glyph_mask(glyph_src)
    cover = (gm[INNER] > 0.5).mean() if gm is not None else 1.0
    soft = ((glyph_src[..., 3] > 0.05) & (glyph_src[..., 3] < 0.95))[INNER].mean()
    haze = gm is None or (not wrapped and (soft > 0.25 or cover > 0.55))
    out = {theme: (tinted(dark, col) if haze else compose(gm, grgb, col)) for theme, col in colours.items()}
    return out
