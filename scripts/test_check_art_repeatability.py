#!/usr/bin/env python3
"""Unit tests for the art repeatability checker (scripts/check-art-repeatability.py).

Hermetic: builds a throwaway repo tree per test and drives the checker over it.
The audio half needs ffmpeg to encode and decode a cue, so it skips without one.
Run with:

    python3 -m unittest scripts.test_check_art_repeatability
"""

from __future__ import annotations

import importlib.util
import io
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

ROOT = pathlib.Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location(
    "check_art", ROOT / "scripts" / "check-art-repeatability.py")
check_art = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(check_art)

_GSPEC = importlib.util.spec_from_file_location(
    "glyph", ROOT / ".ai" / "skills" / "mc-textures" / "scripts" / "glyph.py")
glyph = importlib.util.module_from_spec(_GSPEC)
_GSPEC.loader.exec_module(glyph)

HAVE_FFMPEG = shutil.which("ffmpeg") is not None

GLYPH_SPEC = """\
ships: assets/coin.png
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


class CheckerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = pathlib.Path(self.tmp.name)
        (self.repo / "art" / "glyphs").mkdir(parents=True)
        (self.repo / "art" / "audio").mkdir(parents=True)
        (self.repo / "assets").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, **kw):
        out = io.StringIO()
        with redirect_stdout(out):
            result = check_art.check_repo(self.repo, **kw)
        return result, out.getvalue()

    def _write_glyph(self, text=GLYPH_SPEC, name="coin.glyph"):
        path = self.repo / "art" / "glyphs" / name
        path.write_text(text)
        return path

    def _render_glyph(self, spec_path, dest="assets/coin.png"):
        subprocess.run(
            [sys.executable, str(check_art.GLYPH), str(spec_path),
             "-o", str(self.repo / dest), "--no-preview"],
            check=True, capture_output=True, cwd=self.repo)

    def test_faithful_asset_passes(self):
        spec = self._write_glyph()
        self._render_glyph(spec)
        (checked, drifted, unlinked), out = self._run(verbose=True)
        self.assertEqual((checked, drifted, unlinked), (1, 0, 0))
        self.assertIn("ok", out)

    def test_hand_patched_asset_is_drift(self):
        spec = self._write_glyph()
        self._render_glyph(spec)
        shipped = self.repo / "assets" / "coin.png"
        px, w, h = glyph.read_png(shipped)
        px[5] = (255, 0, 255, 255)
        glyph.write_png(shipped, px, w, h)
        (checked, drifted, _), out = self._run()
        self.assertEqual((checked, drifted), (1, 1))
        self.assertIn("DRIFT", out)
        self.assertIn("pixels differ", out)

    def test_edited_spec_without_rerender_is_drift(self):
        # The other direction: the spec moved on, the shipped asset didn't.
        spec = self._write_glyph()
        self._render_glyph(spec)
        spec.write_text(GLYPH_SPEC.replace("  g gold", "  g crimson"))
        (_, drifted, _), out = self._run()
        self.assertEqual(drifted, 1)
        self.assertIn("DRIFT", out)

    def test_missing_asset_is_drift(self):
        self._write_glyph()
        (checked, drifted, _), out = self._run()
        self.assertEqual((checked, drifted), (1, 1))
        self.assertIn("missing", out)

    def test_spec_without_ships_is_unlinked_not_drift(self):
        self._write_glyph(GLYPH_SPEC.replace("ships: assets/coin.png\n", ""))
        (checked, drifted, unlinked), out = self._run()
        self.assertEqual((checked, drifted, unlinked), (0, 0, 1))
        self.assertIn("unlinked", out)

    def test_ships_after_the_grid_is_not_read(self):
        # A 'ships:' line below the legend would be a grid row, not a header
        # directive — the parser must not pick it up as a target.
        self._write_glyph(GLYPH_SPEC.replace("ships: assets/coin.png\n", "")
                          + "\n# ships: assets/nope.png\n")
        (checked, _, unlinked), _ = self._run()
        self.assertEqual((checked, unlinked), (0, 1))

    def test_ships_parsers_agree_with_the_renderers(self):
        # The checker skims for 'ships:' to decide what is linked; the renderer
        # parses it to decide what to compare. They must see the same targets.
        spec = self._write_glyph(
            GLYPH_SPEC.replace("ships: assets/coin.png\n",
                               "ships: assets/coin.png\nships: assets/coin-64.png 64\n"))
        self.assertEqual(check_art.glyph_ships(spec),
                         ["assets/coin.png", "assets/coin-64.png"])
        _, _, _, meta, _ = glyph.parse_spec(spec.read_text())
        self.assertEqual(meta["ships"],
                         [("assets/coin.png", None), ("assets/coin-64.png", 64)])

    def test_declared_ladder_tier_is_verified_at_its_size(self):
        spec = self._write_glyph(
            GLYPH_SPEC.replace("ships: assets/coin.png\n",
                               "ships: assets/coin.png\nships: assets/coin-16.png 16\n"))
        self._render_glyph(spec)
        subprocess.run(
            [sys.executable, str(check_art.GLYPH), str(spec), "-o",
             str(self.repo / "assets" / "coin-16.png"), "--scale-to", "16"],
            check=True, capture_output=True, cwd=self.repo)
        (checked, drifted, _), _ = self._run()
        self.assertEqual((checked, drifted), (1, 0))
        # A tier shipped at the wrong size must not pass as "close enough".
        self._render_glyph(spec, dest="assets/coin-16.png")
        (_, drifted, _), out = self._run()
        self.assertEqual(drifted, 1)
        self.assertIn("the spec renders 16×16", out)

    @unittest.skipUnless(HAVE_FFMPEG, "ffmpeg is required to encode a cue")
    def test_audio_specs_are_checked_too(self):
        cue = self.repo / "art" / "audio" / "blip.sfx"
        cue.write_text(json.dumps({
            "subtitle": "t.s.b", "seed": 1, "ships": "assets/blip.ogg",
            "layers": [{"freq": 880, "duration": 0.1}],
        }))
        self.assertEqual(check_art.sfx_ships(cue), ["assets/blip.ogg"])
        (checked, drifted, _), _ = self._run()
        self.assertEqual((checked, drifted), (1, 1))  # nothing shipped yet
        subprocess.run(
            [sys.executable, str(check_art.SFX), str(cue),
             "-o", str(self.repo / "assets" / "blip.ogg"), "--no-report"],
            check=True, capture_output=True, cwd=self.repo)
        (checked, drifted, _), _ = self._run()
        self.assertEqual((checked, drifted), (1, 0))


if __name__ == "__main__":
    unittest.main()
