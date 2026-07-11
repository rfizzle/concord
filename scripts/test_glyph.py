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
