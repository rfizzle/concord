#!/usr/bin/env python3
"""Render an ASCII glyph spec into a Minecraft-ready PNG sprite.

The idea: a language model lays out a fixed character grid far more reliably
than it emits binary image data. So a glyph is authored as a *spec* — a color
`legend` (one character -> one color) plus one or more square `frame` grids of
those characters, one character per pixel — and this script deterministically
rasterizes it to a true-size PNG plus a scaled nearest-neighbor preview you can
actually see.

Multiple frames produce an **animated** texture: a vertical sprite strip
(16 wide × 16·N tall) plus a `<name>.png.mcmeta` sidecar, exactly as vanilla
Minecraft animated textures are packaged. The preview becomes a horizontal
filmstrip so you can eyeball every frame at once.

Zero dependencies: PNGs are encoded with the stdlib (`zlib` + manual chunks),
so this runs anywhere Python 3 does, no `pip install` required.

SPEC FORMAT
-----------
A color `legend:` (shared across all frames) followed by one or more `frame:`
grids. `grid:` is an accepted alias for a single `frame:`. Lines starting with
`#` are comments *outside* a grid; blank lines are ignored. Inside a grid every
non-blank line is a row.

    # prosperity — unlooted-chest sparkle (animated)
    size: 16                # optional; inferred from the grid if omitted
    frametime: 6            # ticks per frame (animated specs only; default 6)
    interpolate: false      # optional; blend between frames

    legend:
      . transparent         # '.' is transparent by convention
      g gold                # #ffd700  (hex, or a named Concord token)
      d diamond             # #4eeaed
      K ink                 # #0a0a0a outline

    frame:                  # frame 1 — <size> rows of <size> legend chars
      ................
      ... (16 rows) ...
    frame:                  # frame 2
      ................
      ... (16 rows) ...

Colors may be:  `transparent` / `none`,  `#RGB`,  `#RRGGBB`,  `#RRGGBBAA`,
or a named token from NAMED_COLORS (the Concord design-system palette).

USAGE
-----
    python3 scripts/glyph.py SPEC.glyph                 # -> SPEC.png (+ .mcmeta if animated) + preview
    python3 scripts/glyph.py SPEC.glyph -o art/marker.png
    python3 scripts/glyph.py - < SPEC.glyph             # spec on stdin
    python3 scripts/glyph.py SPEC.glyph --preview-scale 24 --no-preview
    python3 scripts/glyph.py --list-colors              # dump the named palette
"""

import argparse
import json
import struct
import sys
import zlib
from pathlib import Path

# Concord design-system palette (DESIGN-SYSTEM.md §1–§2). Legend entries may
# reference these names instead of raw hex. Per-mod accents are namespaced so a
# spec can't accidentally borrow another mod's identity color.
NAMED_COLORS = {
    # shared neutrals
    "ink": "#0a0a0a",
    "card": "#1a1a1a",
    "elevated": "#222222",
    "bone": "#e8e0d4",
    "ash": "#a89f93",
    "smoke": "#6b6359",
    # per-mod accents
    "meridian.purple": "#7b2fbe",
    "meridian.gold": "#ffd700",
    "meridian.gold-deep": "#daa520",
    "mercantile.emerald": "#50c878",
    "mercantile.emerald-bright": "#6ddb94",
    "tribulation.crimson": "#dc143c",
    "tribulation.ember": "#ff6b35",
    "prosperity.gold": "#ffd700",
    "prosperity.gold-deep": "#daa520",
    "prosperity.cyan": "#4eeaed",
    # bare convenience aliases (unambiguous accents)
    "emerald": "#50c878",
    "emerald-bright": "#6ddb94",
    "crimson": "#dc143c",
    "ember": "#ff6b35",
    "diamond": "#4eeaed",
    "arcane": "#7b2fbe",
    "gold": "#ffd700",
}

TRANSPARENT = (0, 0, 0, 0)
DEFAULT_FRAMETIME = 6  # ticks (0.3s) — a calm, readable default pulse
_DIRECTIVES = ("grid:", "frame:")


class SpecError(ValueError):
    """A malformed glyph spec, reported with enough context to fix it."""


def parse_color(token):
    """Resolve a legend color token to an (r, g, b, a) tuple."""
    t = token.strip().lower()
    if t in ("transparent", "none", "_"):
        return TRANSPARENT
    if t in NAMED_COLORS:
        t = NAMED_COLORS[t]
    if not t.startswith("#"):
        raise SpecError(
            f"unknown color {token!r} — use #hex or a named token "
            f"(run --list-colors)"
        )
    hexpart = t[1:]
    if len(hexpart) == 3:  # #RGB -> #RRGGBB
        hexpart = "".join(c * 2 for c in hexpart)
    if len(hexpart) == 6:
        hexpart += "ff"
    if len(hexpart) != 8 or any(c not in "0123456789abcdef" for c in hexpart):
        raise SpecError(f"bad hex color {token!r} — expected #RGB/#RRGGBB/#RRGGBBAA")
    return tuple(int(hexpart[i : i + 2], 16) for i in (0, 2, 4, 6))


def parse_spec(text):
    """Parse a glyph spec into (legend, frames, declared_size, anim).

    `frames` is a list of grids; each grid is a list of row strings.
    `anim` carries frametime / interpolate directives (may be empty).
    """
    legend = {}
    frames = []          # list of grids (each a list of row strings)
    current = None       # the grid currently being filled
    declared_size = None
    anim = {}
    mode = None          # None | "legend" | "grid"

    def flush():
        nonlocal current
        if current is not None:
            frames.append(current)
            current = None

    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        low = line.lower()

        # directives take precedence over grid-row collection
        if low in _DIRECTIVES:
            flush()
            current = []
            mode = "grid"
            continue
        if low == "legend:":
            flush()
            mode = "legend"
            continue
        if low.startswith("size:"):
            try:
                declared_size = int(line.split(":", 1)[1].split()[0])
            except (ValueError, IndexError):
                raise SpecError(f"line {lineno}: size: must be an integer")
            continue
        if low.startswith("frametime:"):
            try:
                anim["frametime"] = int(line.split(":", 1)[1].split()[0])
            except (ValueError, IndexError):
                raise SpecError(f"line {lineno}: frametime: must be an integer")
            continue
        if low.startswith("interpolate:"):
            val = line.split(":", 1)[1].strip().lower()
            anim["interpolate"] = val in ("true", "1", "yes")
            continue

        if mode == "grid":
            if not line or line.startswith("#"):
                continue  # blank line or comment between frames
            if " " in line:
                raise SpecError(
                    f"line {lineno}: grid rows cannot contain spaces "
                    f"(use '.' for transparent): {raw!r}"
                )
            current.append(line)
            continue

        # outside a grid, blank lines and comments are noise
        if not line or line.startswith("#"):
            continue

        if mode == "legend":
            parts = line.split(None, 1)
            if len(parts) != 2:
                raise SpecError(f"line {lineno}: legend entry needs 'CHAR COLOR': {line!r}")
            char = parts[0]
            # the color is the first token after the char; a trailing
            # '# comment' is dropped. Hex values contain no spaces.
            color = parts[1].split()[0]
            if len(char) != 1:
                raise SpecError(f"line {lineno}: legend key must be one character: {char!r}")
            legend[char] = parse_color(color)
        else:
            raise SpecError(
                f"line {lineno}: unexpected content before a 'legend:' or 'frame:' "
                f"directive: {line!r}"
            )

    flush()
    if not frames or all(not f for f in frames):
        raise SpecError("spec has no frame grids (need a 'frame:' or 'grid:' section)")
    legend.setdefault(".", TRANSPARENT)
    return legend, frames, declared_size, anim


def build_frames(legend, frames_rows, declared_size):
    """Validate every frame and flatten each to a row-major RGBA list.

    Returns (list_of_pixel_lists, size). Every frame must be square and all
    frames must share the same size.
    """
    out = []
    size = None
    for fi, rows in enumerate(frames_rows, 1):
        if not rows:
            raise SpecError(f"frame {fi} is empty")
        height = len(rows)
        widths = {len(r) for r in rows}
        if len(widths) != 1:
            raise SpecError(
                f"frame {fi}: rows have differing widths {sorted(widths)} — "
                f"every row must be the same length"
            )
        width = widths.pop()
        if width != height:
            raise SpecError(f"frame {fi} is {width}×{height}; glyph frames must be square")
        if size is None:
            size = width
        elif width != size:
            raise SpecError(
                f"frame {fi} is {width}×{width} but frame 1 is {size}×{size} — "
                f"all frames must match"
            )
        if declared_size is not None and declared_size != width:
            raise SpecError(f"declared size: {declared_size} but frame {fi} is {width}×{width}")

        pixels = []
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch not in legend:
                    raise SpecError(
                        f"frame {fi} cell ({x},{y}) uses {ch!r}, not in the legend"
                    )
                pixels.append(legend[ch])
        out.append(pixels)
    return out, size


def stack_vertical(frames_px, size):
    """Concatenate frames top-to-bottom into one sprite-strip pixel list."""
    out = []
    for px in frames_px:
        out.extend(px)
    return out, size, size * len(frames_px)


def make_filmstrip(frames_px, size, sep=1, sep_color=(60, 60, 60, 255)):
    """Lay frames left-to-right with a thin separator, for a preview image."""
    n = len(frames_px)
    width = n * size + (n - 1) * sep
    out = []
    for y in range(size):
        for fi, px in enumerate(frames_px):
            for x in range(size):
                out.append(px[y * size + x])
            if fi < n - 1:
                out.extend([sep_color] * sep)
    return out, width, size


def _png_chunk(tag, data):
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def write_png(path, pixels, width, height):
    """Encode an 8-bit RGBA PNG from a row-major pixel list (stdlib only)."""
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type 0 (None) for each scanline
        for x in range(width):
            raw += bytes(pixels[y * width + x])
    body = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _png_chunk(b"IEND", b"")
    )
    Path(path).write_bytes(body)


def write_mcmeta(path, anim):
    """Write the vanilla animated-texture sidecar next to the sprite strip."""
    data = {
        "animation": {
            "frametime": anim.get("frametime", DEFAULT_FRAMETIME),
            "interpolate": anim.get("interpolate", False),
        }
    }
    Path(path).write_text(json.dumps(data, indent=2) + "\n")


def scale_nearest(pixels, width, height, factor):
    """Nearest-neighbor upscale (keeps pixels crisp, no blur)."""
    out = []
    for y in range(height * factor):
        sy = y // factor
        for x in range(width * factor):
            out.append(pixels[sy * width + (x // factor)])
    return out, width * factor, height * factor


def render_ascii(pixels, width, height):
    """A terminal preview: filled block for opaque cells, space for transparent."""
    lines = []
    for y in range(height):
        row = []
        for x in range(width):
            row.append("·" if pixels[y * width + x][3] == 0 else "█")
        lines.append("".join(row))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render an ASCII glyph spec to a PNG sprite.")
    ap.add_argument("spec", nargs="?", help="path to the glyph spec, or '-' for stdin")
    ap.add_argument("-o", "--out", help="output PNG path (default: SPEC with .png)")
    ap.add_argument("--preview-scale", type=int, default=16,
                    help="nearest-neighbor preview factor (default 16 → 256px for a 16px glyph)")
    ap.add_argument("--no-preview", action="store_true", help="skip the scaled preview PNG")
    ap.add_argument("--list-colors", action="store_true", help="print the named palette and exit")
    args = ap.parse_args(argv)

    if args.list_colors:
        width = max(len(k) for k in NAMED_COLORS)
        for name, hex_ in NAMED_COLORS.items():
            print(f"  {name.ljust(width)}  {hex_}")
        return 0

    if not args.spec:
        ap.error("a spec path (or '-' for stdin) is required")

    if args.spec == "-":
        text = sys.stdin.read()
        default_out = Path("glyph.png")
    else:
        spec_path = Path(args.spec)
        text = spec_path.read_text()
        default_out = spec_path.with_suffix(".png")

    try:
        legend, frames_rows, declared_size, anim = parse_spec(text)
        frames_px, size = build_frames(legend, frames_rows, declared_size)
    except SpecError as e:
        print(f"glyph: {e}", file=sys.stderr)
        return 1

    out = Path(args.out) if args.out else default_out
    out.parent.mkdir(parents=True, exist_ok=True)
    nframes = len(frames_px)

    if nframes == 1:
        write_png(out, frames_px[0], size, size)
        print(render_ascii(frames_px[0], size, size))
        print(f"\n  wrote {out}  ({size}×{size})")
        if not args.no_preview and args.preview_scale > 1:
            spx, sw, sh = scale_nearest(frames_px[0], size, size, args.preview_scale)
            preview = out.with_name(f"{out.stem}@{args.preview_scale}x{out.suffix}")
            write_png(preview, spx, sw, sh)
            print(f"  wrote {preview}  ({sw}×{sh} preview)")
        return 0

    # animated: vertical sprite strip + .mcmeta sidecar
    strip_px, sw, sh = stack_vertical(frames_px, size)
    write_png(out, strip_px, sw, sh)
    mcmeta = out.with_name(out.name + ".mcmeta")
    write_mcmeta(mcmeta, anim)

    for i, px in enumerate(frames_px, 1):
        print(f"frame {i}/{nframes}")
        print(render_ascii(px, size, size))
        print()
    ft = anim.get("frametime", DEFAULT_FRAMETIME)
    print(f"  wrote {out}  ({sw}×{sh} strip, {nframes} frames)")
    print(f"  wrote {mcmeta}  (frametime {ft}, interpolate {anim.get('interpolate', False)})")

    if not args.no_preview and args.preview_scale > 1:
        film_px, fw, fh = make_filmstrip(frames_px, size)
        spx, psw, psh = scale_nearest(film_px, fw, fh, args.preview_scale)
        preview = out.with_name(f"{out.stem}@{args.preview_scale}x{out.suffix}")
        write_png(preview, spx, psw, psh)
        print(f"  wrote {preview}  ({psw}×{psh} filmstrip preview)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
