#!/usr/bin/env python3
"""Unit tests for the vendored glyph renderer (.ai/skills/mc-textures/scripts/glyph.py).

Hermetic: specs are inline strings, all output goes to a temp dir. Run with:

    python3 -m unittest scripts.test_glyph
    python3 scripts/test_glyph.py
"""

from __future__ import annotations

import importlib.util
import io
import json
import pathlib
import struct
import tempfile
import unittest
import zlib
from contextlib import redirect_stderr, redirect_stdout

ROOT = pathlib.Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location(
    "glyph", ROOT / ".ai" / "skills" / "mc-textures" / "scripts" / "glyph.py")
glyph = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(glyph)

STATIC_SPEC = """\
legend:
  . transparent
  g gold
  K ink
frame:
  .KK.
  KggK
  KggK
  .KK.
"""

ANIM_SPEC = """\
frametime: 4
legend:
  . transparent
  g gold
frame:
  g...
  ....
  ....
  ....
frame:
  ....
  .g..
  ....
  ....
"""


def run_main(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = glyph.main(argv)
    return rc, out.getvalue(), err.getvalue()


def png_size(path):
    data = pathlib.Path(path).read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    w, h = struct.unpack(">II", data[16:24])
    return w, h


class ParseTests(unittest.TestCase):
    def test_static_spec_parses(self):
        legend, frames, size, anim, used = glyph.parse_spec(STATIC_SPEC)
        self.assertEqual(len(frames), 1)
        self.assertEqual(used, {"gold", "ink"})
        px, n = glyph.build_frames(legend, frames, size)
        self.assertEqual(n, 4)
        self.assertEqual(px[0][0], (0, 0, 0, 0))          # corner transparent
        self.assertEqual(px[0][5], glyph.parse_color("gold"))

    def test_colors(self):
        self.assertEqual(glyph.parse_color("#f00"), (255, 0, 0, 255))
        self.assertEqual(glyph.parse_color("#11223344"), (0x11, 0x22, 0x33, 0x44))
        self.assertEqual(glyph.parse_color("transparent"), (0, 0, 0, 0))
        with self.assertRaises(glyph.SpecError):
            glyph.parse_color("chartreuse")
        with self.assertRaises(glyph.SpecError):
            glyph.parse_color("#12345")

    def test_errors(self):
        for bad in (
            "legend:\n  . transparent\n",                       # no frames
            "legend:\n  . transparent\nframe:\n  ..\n  ..\n  ..\n",   # non-square
            "legend:\n  . transparent\nframe:\n  ..\n  .\n",    # ragged rows
            "legend:\n  . transparent\nframe:\n  .x\n  ..\n",   # unknown char
            "size: 8\nlegend:\n  . transparent\nframe:\n  ..\n  ..\n",  # size mismatch
            "legend:\n  ab #fff\nframe:\n  ..\n  ..\n",         # multi-char key
        ):
            with self.assertRaises(glyph.SpecError, msg=bad):
                legend, frames, size, anim, used = glyph.parse_spec(bad)
                glyph.build_frames(legend, frames, size)

    def test_frames_must_match_size(self):
        spec = "legend:\n  g gold\nframe:\n  gg\n  gg\nframe:\n  g\n"
        with self.assertRaises(glyph.SpecError):
            legend, frames, size, anim, used = glyph.parse_spec(spec)
            glyph.build_frames(legend, frames, size)


class AnalyzeTests(unittest.TestCase):
    def _analyze(self, spec):
        legend, frames, size, anim, used = glyph.parse_spec(spec)
        px, n = glyph.build_frames(legend, frames, size)
        return glyph.analyze(px, n, used)

    def test_sprite_margin_and_bleed(self):
        lines, warns = self._analyze(
            "legend:\n  . transparent\n  g gold\nframe:\n  ....\n  .gg.\n  .gg.\n  ....\n")
        self.assertTrue(any("transparent 1px margin" in ln for ln in lines))
        self.assertEqual(warns, [])
        lines, warns = self._analyze(
            "legend:\n  g gold\nframe:\n  gg\n  gg\n")
        self.assertTrue(any("full bleed" in ln for ln in lines))

    def test_mixed_edge_warns(self):
        _, warns = self._analyze(
            "legend:\n  . transparent\n  g gold\nframe:\n  g.\n  ..\n")
        self.assertTrue(any("neither" in w for w in warns))

    def test_flat_fill_warns_at_32(self):
        rows = ["g" * 32] * 32
        spec = "legend:\n  g gold\nframe:\n" + "\n".join(f"  {r}" for r in rows) + "\n"
        _, warns = self._analyze(spec)
        self.assertTrue(any("flat fill" in w for w in warns))

    def test_mixed_mod_accents_warn(self):
        _, warns = self._analyze(
            "legend:\n  a meridian.purple\n  b tribulation.ember\nframe:\n  ab\n  ba\n")
        self.assertTrue(any("mixes accents" in w for w in warns))
        _, warns = self._analyze(
            "legend:\n  a meridian.purple\n  b meridian.gold\nframe:\n  ab\n  ba\n")
        self.assertFalse(any("mixes accents" in w for w in warns))


def build_png(rows, width, height, color_type, channels, filters,
              plte=None, trns=None, bit_depth=8, interlace=0):
    """Encode a PNG from raw (unfiltered) scanline byte rows, applying the
    given per-row filter types — exercises every decoder unfilter path."""
    raw = bytearray()
    prev = bytearray(width * channels)
    for y, row in enumerate(rows):
        f = filters[y % len(filters)]
        raw.append(f)
        enc = bytearray(row)
        for i in range(len(row)):
            a = row[i - channels] if i >= channels else 0
            b = prev[i]
            c = prev[i - channels] if i >= channels else 0
            if f == 1:
                enc[i] = (row[i] - a) & 0xFF
            elif f == 2:
                enc[i] = (row[i] - b) & 0xFF
            elif f == 3:
                enc[i] = (row[i] - ((a + b) >> 1)) & 0xFF
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                enc[i] = (row[i] - pred) & 0xFF
        raw += enc
        prev = row
    body = b"\x89PNG\r\n\x1a\n" + glyph._png_chunk(
        b"IHDR", struct.pack(">IIBBBBB", width, height, bit_depth, color_type, 0, 0, interlace))
    if plte is not None:
        body += glyph._png_chunk(b"PLTE", bytes(b for rgb in plte for b in rgb))
    if trns is not None:
        body += glyph._png_chunk(b"tRNS", bytes(trns))
    body += glyph._png_chunk(b"IDAT", zlib.compress(bytes(raw)))
    body += glyph._png_chunk(b"IEND", b"")
    return body


class FromPngTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_rgba_round_trip(self):
        legend, frames, size, anim, used = glyph.parse_spec(STATIC_SPEC)
        frames_px, n = glyph.build_frames(legend, frames, size)
        src = self.dir / "m.png"
        glyph.write_png(src, frames_px[0], n, n)
        rc, out, err = run_main(["--from-png", str(src)])
        self.assertEqual(rc, 0, err)
        self.assertIn("pixel-identical", out)
        legend2, frames2, size2, _, _ = glyph.parse_spec((self.dir / "m.glyph").read_text())
        px2, n2 = glyph.build_frames(legend2, frames2, size2)
        self.assertEqual(px2[0], frames_px[0])

    def test_all_filters_decode(self):
        # 4×5 RGBA with one row per filter type 0-4.
        rows = [bytearray((x * 40 + y * 25) % 256 for x in range(4 * 4)) for y in range(5)]
        data = build_png(rows, 4, 5, color_type=6, channels=4, filters=[0, 1, 2, 3, 4])
        p = self.dir / "f.png"
        p.write_bytes(data)
        px, w, h = glyph.read_png(p)
        self.assertEqual((w, h), (4, 5))
        for y, row in enumerate(rows):
            for x in range(4):
                self.assertEqual(px[y * 4 + x], tuple(row[x * 4:x * 4 + 4]), f"({x},{y})")

    def test_rgb_and_gray_get_opaque_alpha(self):
        rows = [bytearray([10, 20, 30, 200, 100, 50])]  # 2×1 RGB
        p = self.dir / "rgb.png"
        p.write_bytes(build_png(rows, 2, 1, color_type=2, channels=3, filters=[0]))
        px, _, _ = glyph.read_png(p)
        self.assertEqual(px, [(10, 20, 30, 255), (200, 100, 50, 255)])
        rows = [bytearray([0, 128, 255])]  # 3×1 grayscale
        p = self.dir / "gray.png"
        p.write_bytes(build_png(rows, 3, 1, color_type=0, channels=1, filters=[0]))
        px, _, _ = glyph.read_png(p)
        self.assertEqual(px, [(0, 0, 0, 255), (128, 128, 128, 255), (255, 255, 255, 255)])

    def test_palette_with_trns(self):
        rows = [bytearray([0, 1]), bytearray([1, 0])]  # 2×2, indices into PLTE
        p = self.dir / "pal.png"
        p.write_bytes(build_png(rows, 2, 2, color_type=3, channels=1, filters=[0],
                                plte=[(255, 0, 0), (0, 255, 0)], trns=[0, 255]))
        px, _, _ = glyph.read_png(p)
        self.assertEqual(px[0], (255, 0, 0, 0))    # tRNS makes index 0 transparent
        self.assertEqual(px[1], (0, 255, 0, 255))

    def test_rejections(self):
        rows = [bytearray([0, 0, 0, 255] * 2)]  # 2×1 RGBA — not square
        p = self.dir / "ns.png"
        p.write_bytes(build_png(rows, 2, 1, color_type=6, channels=4, filters=[0]))
        with self.assertRaises(glyph.SpecError):
            glyph.transcribe_png(p, self.dir / "ns.glyph")
        p16 = self.dir / "deep.png"
        p16.write_bytes(build_png(rows, 2, 1, color_type=6, channels=4,
                                  filters=[0], bit_depth=16))
        with self.assertRaises(glyph.SpecError):
            glyph.read_png(p16)
        pi = self.dir / "il.png"
        pi.write_bytes(build_png(rows, 2, 1, color_type=6, channels=4,
                                 filters=[0], interlace=1))
        with self.assertRaises(glyph.SpecError):
            glyph.read_png(pi)
        notpng = self.dir / "x.png"
        notpng.write_bytes(b"hello")
        with self.assertRaises(glyph.SpecError):
            glyph.read_png(notpng)

    def test_too_many_colors_rejected(self):
        n = 16  # 256 unique opaque colors > pool
        px = [(x * 16 % 256, y * 16 % 256, (x ^ y) * 16 % 256, 255)
              for y in range(n) for x in range(n)]
        p = self.dir / "noisy.png"
        glyph.write_png(p, px, n, n)
        with self.assertRaises(glyph.SpecError) as cm:
            glyph.transcribe_png(p, self.dir / "noisy.glyph")
        self.assertIn("quantize", str(cm.exception))

    def test_partial_alpha_survives(self):
        px = [(255, 0, 0, 128), (0, 0, 0, 0), (0, 0, 0, 0), (255, 0, 0, 128)]
        p = self.dir / "pa.png"
        glyph.write_png(p, px, 2, 2)
        glyph.transcribe_png(p, self.dir / "pa.glyph")
        text = (self.dir / "pa.glyph").read_text()
        self.assertIn("#ff000080", text)


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _spec_file(self, content, name="t.glyph"):
        p = self.dir / name
        p.write_text(content)
        return p

    def test_static_render(self):
        spec = self._spec_file(STATIC_SPEC)
        out = self.dir / "t.png"
        rc, _, _ = run_main([str(spec), "-o", str(out)])
        self.assertEqual(rc, 0)
        self.assertEqual(png_size(out), (4, 4))
        self.assertEqual(png_size(self.dir / "t@16x.png"), (64, 64))

    def test_tile_preview(self):
        spec = self._spec_file(STATIC_SPEC)
        out = self.dir / "t.png"
        rc, _, _ = run_main([str(spec), "-o", str(out), "--tile-preview", "--no-preview"])
        self.assertEqual(rc, 0)
        w, h = png_size(self.dir / "t@2x2.png")
        self.assertEqual(w, h)
        self.assertEqual(w % 8, 0)  # 2×2 of a 4px glyph, integer-scaled

    def test_animated_strip_and_mcmeta(self):
        spec = self._spec_file(ANIM_SPEC)
        out = self.dir / "a.png"
        rc, _, _ = run_main([str(spec), "-o", str(out), "--no-preview"])
        self.assertEqual(rc, 0)
        self.assertEqual(png_size(out), (4, 8))  # 2 frames stacked
        meta = json.loads((self.dir / "a.png.mcmeta").read_text())
        self.assertEqual(meta["animation"]["frametime"], 4)

    def test_apng_preview_structure(self):
        spec = self._spec_file(ANIM_SPEC)
        out = self.dir / "a.png"
        rc, _, _ = run_main([str(spec), "-o", str(out)])
        self.assertEqual(rc, 0)
        data = (self.dir / "a@16x-anim.png").read_bytes()
        self.assertIn(b"acTL", data)
        self.assertEqual(data.count(b"fcTL"), 2)
        self.assertEqual(data.count(b"fdAT"), 1)

    def test_split_frames(self):
        spec = self._spec_file(ANIM_SPEC)
        out = self.dir / "a.png"
        rc, _, _ = run_main([str(spec), "-o", str(out), "--split-frames", "--no-preview"])
        self.assertEqual(rc, 0)
        self.assertEqual(png_size(self.dir / "a_0.png"), (4, 4))
        self.assertEqual(png_size(self.dir / "a_1.png"), (4, 4))
        self.assertFalse((self.dir / "a.png.mcmeta").exists())

    def test_split_frames_rejects_static(self):
        spec = self._spec_file(STATIC_SPEC)
        rc, _, err = run_main([str(spec), "-o", str(self.dir / "t.png"), "--split-frames"])
        self.assertEqual(rc, 1)
        self.assertIn("animated", err)

    def test_scale_to(self):
        spec = self._spec_file(STATIC_SPEC)
        out = self.dir / "t128.png"
        rc, _, _ = run_main([str(spec), "-o", str(out), "--scale-to", "128"])
        self.assertEqual(rc, 0)
        self.assertEqual(png_size(out), (128, 128))

    def test_scale_to_rejects_non_multiple(self):
        spec = self._spec_file(STATIC_SPEC)
        rc, _, err = run_main([str(spec), "-o", str(self.dir / "t.png"), "--scale-to", "10"])
        self.assertEqual(rc, 1)
        self.assertIn("integer multiple", err)

    def test_scanlines_decode(self):
        # The compressed IDAT must decode to (1 filter byte + 4·w) per row.
        spec = self._spec_file(STATIC_SPEC)
        out = self.dir / "t.png"
        run_main([str(spec), "-o", str(out), "--no-preview"])
        data = out.read_bytes()
        idat_start = data.index(b"IDAT") + 4
        idat_len = struct.unpack(">I", data[idat_start - 8:idat_start - 4])[0]
        raw = zlib.decompress(data[idat_start:idat_start + idat_len])
        self.assertEqual(len(raw), 4 * (1 + 4 * 4))

    def test_shipped_examples_render(self):
        examples = ROOT / ".ai" / "skills" / "mc-textures" / "examples"
        for spec in sorted(examples.glob("*.glyph")):
            rc, _, err = run_main(
                [str(spec), "-o", str(self.dir / f"{spec.stem}.png"), "--no-preview"])
            self.assertEqual(rc, 0, f"{spec.name}: {err}")


if __name__ == "__main__":
    unittest.main()
