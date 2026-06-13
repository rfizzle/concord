#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["pillow>=10"]
# ///
"""Render an ASCII glyph spec to a PNG sprite — Pillow backend.

A drop-in alternative to `glyph.py` that uses Pillow instead of the stdlib PNG
encoder. Same spec format, same CLI, same named palette — it reuses the parser
from `glyph.py` so the two differ only in the rasterization backend.

Bonus for animated specs (multiple frames): this backend also emits an animated
**GIF** preview (frames composited over a checkerboard so transparency reads),
so you can watch the motion, not just a filmstrip of stills. That's the main
reason you might reach for this one over the zero-dependency `glyph.py`.

Run it with uv (auto-installs Pillow into an ephemeral env — no global install):

    uv run scripts/glyph_pil.py SPEC.glyph
    uv run scripts/glyph_pil.py SPEC.glyph -o art/marker.png --preview-scale 24
    uv run scripts/glyph_pil.py - < SPEC.glyph
"""

import argparse
import sys
from pathlib import Path

# Reuse the spec parser + palette from the stdlib renderer (same directory),
# so spec format and named colors stay single-sourced.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from glyph import (  # noqa: E402
    DEFAULT_FRAMETIME,
    NAMED_COLORS,
    SpecError,
    build_frames,
    make_filmstrip,
    parse_spec,
    render_ascii,
    stack_vertical,
    write_mcmeta,
)

from PIL import Image  # noqa: E402


def to_image(pixels, width, height):
    img = Image.new("RGBA", (width, height))
    img.putdata([tuple(p) for p in pixels])
    return img


def checkerboard(size, factor, a=(40, 40, 40, 255), b=(58, 58, 58, 255)):
    """A dark 2-square checkerboard the size of one scaled frame."""
    bg = Image.new("RGBA", (size * factor, size * factor))
    cell = max(1, factor)  # one source-pixel per check
    px = []
    for y in range(size * factor):
        for x in range(size * factor):
            px.append(a if ((x // cell) + (y // cell)) % 2 == 0 else b)
    bg.putdata(px)
    return bg


def write_gif(path, frames_px, size, factor, frametime):
    """Animated GIF preview: each frame nearest-scaled over a checkerboard."""
    duration_ms = max(20, int(frametime * 50))  # 1 tick = 50ms
    bg = checkerboard(size, factor)
    rendered = []
    for px in frames_px:
        frame = to_image(px, size, size).resize((size * factor, size * factor), Image.NEAREST)
        composite = Image.alpha_composite(bg.copy(), frame)
        rendered.append(composite.convert("P", palette=Image.ADAPTIVE))
    rendered[0].save(
        path,
        save_all=True,
        append_images=rendered[1:],
        duration=duration_ms,
        loop=0,
        disposal=2,
    )


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render an ASCII glyph spec to a PNG (Pillow backend).")
    ap.add_argument("spec", nargs="?", help="path to the glyph spec, or '-' for stdin")
    ap.add_argument("-o", "--out", help="output PNG path (default: SPEC with .png)")
    ap.add_argument("--preview-scale", type=int, default=16,
                    help="nearest-neighbor preview factor (default 16 → 256px for a 16px glyph)")
    ap.add_argument("--no-preview", action="store_true", help="skip the scaled/animated preview")
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
    scale = args.preview_scale

    if nframes == 1:
        img = to_image(frames_px[0], size, size)
        img.save(out)
        print(render_ascii(frames_px[0], size, size))
        print(f"\n  wrote {out}  ({size}×{size})")
        if not args.no_preview and scale > 1:
            preview = out.with_name(f"{out.stem}@{scale}x{out.suffix}")
            img.resize((size * scale, size * scale), Image.NEAREST).save(preview)
            print(f"  wrote {preview}  ({size * scale}×{size * scale} preview)")
        return 0

    # animated: vertical sprite strip + .mcmeta sidecar
    strip_px, sw, sh = stack_vertical(frames_px, size)
    to_image(strip_px, sw, sh).save(out)
    mcmeta = out.with_name(out.name + ".mcmeta")
    write_mcmeta(mcmeta, anim)

    for i, px in enumerate(frames_px, 1):
        print(f"frame {i}/{nframes}")
        print(render_ascii(px, size, size))
        print()
    ft = anim.get("frametime", DEFAULT_FRAMETIME)
    print(f"  wrote {out}  ({sw}×{sh} strip, {nframes} frames)")
    print(f"  wrote {mcmeta}  (frametime {ft}, interpolate {anim.get('interpolate', False)})")

    if not args.no_preview and scale > 1:
        film_px, fw, fh = make_filmstrip(frames_px, size)
        film = out.with_name(f"{out.stem}@{scale}x{out.suffix}")
        to_image(film_px, fw, fh).resize((fw * scale, fh * scale), Image.NEAREST).save(film)
        print(f"  wrote {film}  ({fw * scale}×{fh * scale} filmstrip preview)")

        gif = out.with_name(f"{out.stem}@{scale}x.gif")
        write_gif(gif, frames_px, size, scale, ft)
        print(f"  wrote {gif}  (animated preview, {ft * 50}ms/frame)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
