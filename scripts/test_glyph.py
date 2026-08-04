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
import shutil
import struct
import sys
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


# A 16px checkerboard: big enough to downscale several tiers, and detailed
# enough that two resampling filters cannot agree by accident.
_BIG_SPEC = "legend:\n  g gold\n  K ink\nframe:\n" + "\n".join(
    "  " + ("gK" * 8 if y % 2 else "Kg" * 8) for y in range(16)) + "\n"


def run_main(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = glyph.main(argv)
    return rc, out.getvalue(), err.getvalue()


def analyze_spec(spec_text):
    """Parse, build, and analyze a spec. Returns (lines, warnings, notes) with
    the two severities split, which is how the callers read them."""
    legend, frames, size, meta, used = glyph.parse_spec(spec_text)
    px, n = glyph.build_frames(legend, frames, size)
    lines, findings = glyph.analyze(px, n, used, meta.get("raw_hex", ()),
                                    meta.get("palette", "tokens"),
                                    meta.get("kind"), meta.get("edge"))
    return (lines,
            [t for sev, t in findings if sev == "warning"],
            [t for sev, t in findings if sev == "note"])


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
        lines, warns, _ = analyze_spec(spec)
        return lines, warns

    def test_sprite_margin_and_bleed(self):
        lines, warns = self._analyze(
            "kind: sprite\nlegend:\n  . transparent\n  g gold\n"
            "frame:\n  ....\n  .gg.\n  .gg.\n  ....\n")
        self.assertTrue(any("transparent 1px margin" in ln for ln in lines))
        self.assertEqual(warns, [])
        lines, warns = self._analyze(
            "kind: block\nlegend:\n  g gold\nframe:\n  gg\n  gg\n")
        self.assertTrue(any("full bleed" in ln for ln in lines))

    def test_mixed_edge_warns_when_the_kind_implies_one(self):
        mixed = "legend:\n  . transparent\n  g gold\nframe:\n  g.\n  ..\n"
        _, warns = self._analyze("kind: sprite\n" + mixed)
        self.assertTrue(any("1px transparent margin" in w for w in warns))
        _, warns = self._analyze("kind: block\n" + mixed)
        self.assertTrue(any("bleeds to all four edges" in w for w in warns))
        # A UI element may bleed on some edges and not others by design.
        _, warns = self._analyze("kind: ui\n" + mixed)
        self.assertEqual(warns, [])
        # An atlas is only ever read through sub-windows, so its outline says
        # nothing about how it is drawn.
        _, warns = self._analyze("kind: atlas\n" + mixed)
        self.assertEqual(warns, [])
        # Undeclared: the geometry is genuinely ambiguous, so it is a note.
        _, warns, notes = analyze_spec(mixed)
        self.assertEqual(warns, [])
        self.assertTrue(any("could not be inferred" in n for n in notes))

    def test_a_sprite_may_declare_the_edge_it_draws(self):
        # The quality bar has always allowed a motif to reach its border on
        # purpose. The `edge:` line is where the spec says so — and the warning
        # that fires without it names that line rather than an option that
        # would only trade one warning for another.
        mixed = "legend:\n  . transparent\n  g gold\nframe:\n  g.\n  ..\n"
        bleed = "legend:\n  g gold\nframe:\n  gg\n  gg\n"

        _, warns = self._analyze("kind: sprite\n" + mixed)
        self.assertTrue(any("edge: shaped" in w for w in warns))
        _, warns = self._analyze("kind: sprite\nedge: shaped\n" + mixed)
        self.assertEqual(warns, [])

        _, warns = self._analyze("kind: sprite\n" + bleed)
        self.assertTrue(any("edge: bleed" in w for w in warns))
        _, warns = self._analyze("kind: sprite\nedge: bleed\n" + bleed)
        self.assertEqual(warns, [])

    def test_a_declared_edge_is_measured_not_trusted(self):
        mixed = "legend:\n  . transparent\n  g gold\nframe:\n  g.\n  ..\n"
        lines, warns = self._analyze("kind: sprite\nedge: bleed\n" + mixed)
        self.assertTrue(any("declares 'edge: bleed'" in w for w in warns))
        self.assertTrue(any("declared: bleed" in ln for ln in lines))

    def test_a_block_cannot_declare_its_way_out_of_bleeding(self):
        # A side face that stops short of its border shows the void where
        # copies meet, whatever the spec meant by it.
        mixed = "kind: block\nedge: shaped\nlegend:\n  . transparent\n  g gold\n"
        _, warns = self._analyze(mixed + "frame:\n  g.\n  ..\n")
        self.assertTrue(any("bleeds to all four edges" in w for w in warns))

    def test_a_particle_spends_its_whole_canvas(self):
        # A 1px ring costs 75% of a 4px canvas — the margin rule is a sprite
        # rule, and a mote is not a sprite.
        full = "legend:\n  g gold\nframe:\n  gg\n  gg\n"
        _, warns = self._analyze("kind: particle\n" + full)
        self.assertEqual(warns, [])

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


class AccentOwnershipTests(unittest.TestCase):
    """The mixed-accent check reads ownership, not spelling.

    An accent belongs to its mod however a legend writes it, so the bare alias
    block cannot be used to opt out of DESIGN-SYSTEM.md §2 rule 1. The shared
    material tones are the deliberate exception.
    """

    def _warns(self, legend):
        _, warns, _ = analyze_spec(f"legend:\n{legend}frame:\n  ab\n  ba\n")
        return [w for w in warns if "mixes accents" in w]

    def test_bare_alias_resolves_to_its_owning_mod(self):
        # `crimson` is Tribulation's; pairing it with Mercantile's emerald is
        # the same violation as `tribulation.crimson` would be.
        self.assertTrue(self._warns("  a mercantile.emerald\n  b crimson\n"))

    def test_bare_alias_of_the_same_mod_is_clean(self):
        # Mixed spellings of one mod's own accents are only a style choice.
        self.assertFalse(self._warns("  a tribulation.crimson\n  b ember\n"))

    def test_alias_whose_name_does_not_carry_its_mod(self):
        # `arcane` is meridian.purple and `diamond` is prosperity.cyan — the
        # alias names match no prefix, so ownership has to come from the colour.
        self.assertTrue(self._warns("  a arcane\n  b tribulation.crimson\n"))
        self.assertTrue(self._warns("  a diamond\n  b cultivation.leaf\n"))

    def test_bare_own_accent_with_a_foreign_namespaced_one_warns(self):
        # A Tribulation glyph reaching for a named Prosperity accent. Counting
        # only namespaced tokens saw one prefix here and stayed silent.
        self.assertTrue(self._warns(
            "  a crimson\n  b prosperity.gold-deep\n"))

    def test_ramp_step_of_a_bare_alias_resolves(self):
        # Resolution has to survive the ramp-base stripping parse_spec does.
        self.assertTrue(self._warns("  a crimson-1\n  b mercantile.emerald+1\n"))

    def test_shared_material_tone_is_owned_by_no_mod(self):
        self.assertEqual(glyph.ACCENT_OWNERS["metal.gold"], frozenset())
        self.assertFalse(self._warns("  a mercantile.emerald\n  b metal.gold\n"))
        self.assertFalse(self._warns("  a metal.gold\n  b metal.gold-deep\n"))

    def test_bare_gold_is_the_shared_tone_not_either_brand(self):
        # Meridian and Prosperity both list #ffd700 as an accent (§2), so the
        # metal carries no one's identity and the bare spelling names it.
        self.assertEqual(glyph.ACCENT_OWNERS["gold"], frozenset())
        self.assertFalse(self._warns("  a mercantile.emerald\n  b gold\n"))

    def test_namespaced_gold_still_belongs_to_its_mod(self):
        # The shared tone does not launder the branded spellings.
        self.assertTrue(self._warns(
            "  a meridian.gold\n  b tribulation.crimson\n"))

    def test_neutrals_are_owned_by_no_mod(self):
        for token in ("ink", "card", "elevated", "bone", "ash", "smoke"):
            self.assertEqual(glyph.ACCENT_OWNERS[token], frozenset(), token)

    def test_warning_names_the_offending_tokens(self):
        # Reporting bare mod names alone would tell a spec whose only Meridian
        # colour is spelled `arcane` that it mixes in a mod it never mentions.
        warns = self._warns("  a arcane\n  b tribulation.crimson\n")
        self.assertTrue(any("meridian (arcane)" in w for w in warns), warns)
        self.assertTrue(
            any("tribulation (tribulation.crimson)" in w for w in warns), warns)

    def test_every_bare_token_is_a_neutral_a_metal_or_an_owned_alias(self):
        # Guards the next palette addition: a bare entry that is neither a
        # role, a material, nor traceable to an accent is a hole in the rule.
        for token in glyph.NAMED_COLORS:
            if "." in token:
                continue
            targets = glyph._alias_targets(token)
            if not targets:
                self.assertEqual(glyph.ACCENT_OWNERS[token], frozenset(), token)
                continue
            prefixes = {t.split(".", 1)[0] for t in targets}
            shared = prefixes & set(glyph.SHARED_NAMESPACES)
            self.assertTrue(shared or glyph.ACCENT_OWNERS[token], token)

    def test_ownership_is_derived_from_the_palette(self):
        # Every namespaced accent resolves to its own prefix, so adding one
        # teaches the check about it without a second table to keep in step.
        for token in glyph.NAMED_COLORS:
            if "." not in token:
                continue
            prefix = token.split(".", 1)[0]
            want = (frozenset() if prefix in glyph.SHARED_NAMESPACES
                    else frozenset((prefix,)))
            self.assertEqual(glyph.ACCENT_OWNERS[token], want, token)


class RampTests(unittest.TestCase):
    def test_step_tokens_resolve(self):
        base = glyph.parse_color("mercantile.emerald")
        light = glyph.parse_color("mercantile.emerald+2")
        dark = glyph.parse_color("mercantile.emerald-2")
        self.assertGreater(sum(light[:3]), sum(base[:3]))
        self.assertLess(sum(dark[:3]), sum(base[:3]))
        self.assertEqual(glyph.parse_color("gold+0"), glyph.parse_color("gold"))

    def test_ramp_is_monotonic_in_value(self):
        # Every step must be a distinct tone, ordered highlight -> occlusion,
        # or the "3-5 step tonal ramp" it exists to serve collapses.
        tones = [glyph.parse_color(f"instinct.rose{s:+d}") if s else
                 glyph.parse_color("instinct.rose")
                 for s in glyph.ramp_steps(5)]
        values = [max(c[:3]) for c in tones]
        self.assertEqual(values, sorted(values, reverse=True))
        self.assertEqual(len(set(tones)), len(tones))

    def test_shadow_cools_and_highlight_warms(self):
        base = glyph.parse_color("tribulation.crimson")
        h_base, _, _ = glyph._rgb_to_hsv(*base[:3])
        h_dark, _, _ = glyph._rgb_to_hsv(*glyph.shade(base, -2)[:3])
        h_light, _, _ = glyph._rgb_to_hsv(*glyph.shade(base, 2)[:3])
        # Crimson sits at ~348°. The cool pole (240°) is the short way down
        # through 300, so a shadow step lowers the hue; the warm pole (50°) is
        # the short way up through 360/0, so a highlight step wraps past red.
        self.assertLess(h_dark, h_base)
        self.assertGreater(h_dark, glyph._COOL_HUE)
        self.assertLess(h_light, 60.0)

    def test_neutral_token_keeps_hue(self):
        # ink/bone/ash have no hue to rotate; shading must not invent one.
        for step in (-2, 2):
            r, g, b, _ = glyph.shade((128, 128, 128, 255), step)
            self.assertEqual((r, g), (g, b))

    def test_ramp_step_records_base_token(self):
        _, _, _, _, used = glyph.parse_spec(
            "legend:\n  a mercantile.emerald-2\n  b mercantile.emerald\n"
            "frame:\n  ab\n  ba\n")
        self.assertEqual(used, {"mercantile.emerald"})

    def test_ramp_step_still_trips_mixed_accents(self):
        _, warns, _ = analyze_spec(
            "legend:\n  a meridian.purple-1\n  b tribulation.ember+1\n"
            "frame:\n  ab\n  ba\n")
        self.assertTrue(any("mixes accents" in w for w in warns))

    def test_hyphenated_token_is_not_a_ramp_step(self):
        self.assertEqual(glyph.parse_color("emerald-bright"),
                         glyph.parse_color("#6ddb94"))
        self.assertEqual(glyph.split_ramp_token("emerald-bright"),
                         ("emerald-bright", 0))

    def test_bad_ramp_tokens_rejected(self):
        for bad in ("nosuch-2", "emerald-9", "emerald+7"):
            with self.assertRaises(glyph.SpecError, msg=bad):
                glyph.parse_color(bad)

    def test_ramp_command_output(self):
        rc, out, _ = run_main(["--ramp", "prosperity.gold", "--ramp-steps", "3"])
        self.assertEqual(rc, 0)
        self.assertIn("prosperity.gold+1", out)
        self.assertIn("prosperity.gold-1", out)
        self.assertEqual(out.count("prosperity.gold"), 4)  # header + 3 steps
        rc, _, err = run_main(["--ramp", "nosuchtoken"])
        self.assertEqual(rc, 1)
        self.assertIn("unknown token", err)

    def test_ramp_steps_are_shadow_biased(self):
        self.assertEqual(glyph.ramp_steps(3), [1, 0, -1])
        self.assertEqual(glyph.ramp_steps(4), [1, 0, -1, -2])
        self.assertEqual(glyph.ramp_steps(5), [2, 1, 0, -1, -2])


def sprite_spec(rows, legend="  . transparent\n  E mercantile.emerald\n"
                            "  e mercantile.emerald-bright\n  K ink\n"):
    return "legend:\n" + legend + "frame:\n" + "\n".join(f"  {r}" for r in rows) + "\n"


def filled_box(size, char="E", margin=1, outline=None):
    """A centred filled square, optionally wrapped in an outline character."""
    rows = []
    for y in range(size):
        row = ""
        for x in range(size):
            inside = margin <= x < size - margin and margin <= y < size - margin
            if not inside:
                row += "."
            elif outline and (x in (margin, size - margin - 1)
                              or y in (margin, size - margin - 1)):
                row += outline
            else:
                row += char
        rows.append(row)
    return rows


class QualityCheckTests(unittest.TestCase):
    def _analyze(self, spec):
        lines, warns, _ = analyze_spec(spec)
        return lines, warns

    def test_flat_fill_warns_below_32px(self):
        # The gate used to start at 32px, so the most common authoring size was
        # never checked at all.
        _, warns = self._analyze(sprite_spec(filled_box(16)))
        self.assertTrue(any("flat fill" in w for w in warns))

    def test_flat_threshold_clears_the_shipped_references(self):
        # The busiest legitimate flat share in the shipped set is an 11px UI
        # button at 62%; the small-size bar has to sit above that.
        for spec in sorted((ROOT / ".ai" / "skills" / "mc-textures" / "examples")
                           .glob("*.glyph")):
            _, warns = self._analyze(spec.read_text())
            self.assertFalse(any("flat fill" in w for w in warns), spec.name)

    def test_missing_outline_warns(self):
        _, warns = self._analyze(sprite_spec(filled_box(16)))
        self.assertTrue(any("silhouette edge is dark" in w for w in warns))

    def test_ink_outline_satisfies_the_check(self):
        lines, warns = self._analyze(sprite_spec(filled_box(16, outline="K")))
        self.assertFalse(any("silhouette edge" in w for w in warns))
        self.assertTrue(any("outline:  100%" in ln for ln in lines))

    def test_outline_check_skips_blocks_and_tiny_motifs(self):
        # A block bleeds to every edge, so it has no silhouette to wrap.
        _, warns = self._analyze(sprite_spec(["E" * 16] * 16))
        self.assertFalse(any("silhouette edge" in w for w in warns))
        # A spark or pip is too small to carry an outline; the shipped glowing
        # motifs (sparkles, motes) are all well under the area gate.
        small = filled_box(16, margin=6)          # 4×4 = 16 opaque px
        _, warns = self._analyze(sprite_spec(small))
        self.assertFalse(any("silhouette edge" in w for w in warns))

    def test_detached_pieces_are_reported_not_warned(self):
        # Shipped art carries deliberate detached pixels (a glint, a chain
        # link), so this is information for review, not a defect.
        rows = [list(r) for r in filled_box(16, margin=5, outline="K")]
        rows[1][14] = "E"
        spec = sprite_spec(["".join(r) for r in rows])
        lines, warns = self._analyze(spec)
        self.assertTrue(any("pieces:" in ln and "2 detached" in ln for ln in lines))
        self.assertFalse(any("detached" in w for w in warns))

    def test_identical_animation_frame_warns(self):
        moving = "\n".join("  " + ("gK" if i % 2 else "Kg") for i in range(2))
        still = "\n".join("  KK" for _ in range(2))
        spec = ("frametime: 4\nlegend:\n  K ink\n  g gold\n"
                f"frame:\n{moving}\nframe:\n{still}\nframe:\n{still}\n")
        _, warns = self._analyze(spec)
        self.assertTrue(any("frame 3 repeats frame 2" in w for w in warns))

    def test_repeat_across_the_loop_wrap_is_flagged(self):
        # A vanilla animation loops, so the last frame runs straight into the
        # first: an A,B,A cycle stalls for two frametimes at the seam. A ping
        # pong that reads smoothly is A,B,C,B — no two adjacent frames match,
        # wrap included.
        a = "\n".join("  KK" for _ in range(2))
        b = "\n".join("  gg" for _ in range(2))
        c = "\n".join("  Kg" for _ in range(2))
        head = "frametime: 4\nlegend:\n  K ink\n  g gold\n"
        _, warns = self._analyze(f"{head}frame:\n{a}\nframe:\n{b}\nframe:\n{a}\n")
        self.assertTrue(any("frame 1 repeats frame 3" in w for w in warns))
        _, warns = self._analyze(
            f"{head}frame:\n{a}\nframe:\n{b}\nframe:\n{c}\nframe:\n{b}\n")
        self.assertFalse(any("repeats" in w for w in warns))

    def test_vendored_examples_pass_every_check(self):
        examples = ROOT / ".ai" / "skills" / "mc-textures" / "examples"
        for spec in sorted(examples.glob("*.glyph")):
            _, warns = self._analyze(spec.read_text())
            self.assertEqual(warns, [], f"{spec.name} trips a quality warning")


def gradient_spec(axis="h", size=16):
    """A smooth ramp across one axis — the classic tile that does not wrap."""
    legend = "".join(f"  {chr(97 + i)} #{20 + i * 14:02x}{20 + i * 14:02x}"
                     f"{20 + i * 14:02x}\n" for i in range(size))
    rows = ["".join(chr(97 + (x if axis == "h" else y)) for x in range(size))
            for y in range(size)]
    return ("palette: free\nlegend:\n" + legend + "frame:\n"
            + "\n".join(f"  {r}" for r in rows) + "\n")


class SeamTests(unittest.TestCase):
    def _analyze(self, spec):
        lines, warns, _ = analyze_spec(spec)
        return lines, warns

    def test_reference_block_tiles_cleanly(self):
        spec = (ROOT / ".ai" / "skills" / "mc-textures" / "examples"
                / "block-stone-bricks.glyph")
        lines, warns = self._analyze(spec.read_text())
        self.assertFalse(any("join breaks" in w for w in warns))
        self.assertIn("seam:     0% of the left/right join and 0%", "\n".join(lines))

    def test_gradient_that_does_not_wrap_warns(self):
        _, warns = self._analyze(gradient_spec("h"))
        self.assertTrue(any("left/right join breaks" in w for w in warns))
        self.assertFalse(any("top/bottom join breaks" in w for w in warns))
        _, warns = self._analyze(gradient_spec("v"))
        self.assertTrue(any("top/bottom join breaks" in w for w in warns))

    def test_hard_edges_that_tile_are_not_flagged(self):
        # Vertical stripes jump hard at the wrap and tile perfectly: the same
        # jump already occurs inside. Comparing the seam against the texture's
        # own gradients is what tells these apart from a broken gradient.
        stripes = ["K" * 8 + "b" * 8] * 16
        spec = "legend:\n  K ink\n  b bone\nframe:\n" + "\n".join(
            f"  {r}" for r in stripes) + "\n"
        _, warns = self._analyze(spec)
        self.assertFalse(any("join breaks" in w for w in warns))

    def test_noise_tiles_are_not_flagged(self):
        import random
        rnd = random.Random(11)
        chars = "abcdefgh"
        legend = "".join(f"  {c} #{60 + i * 18:02x}{60 + i * 18:02x}"
                         f"{60 + i * 18:02x}\n" for i, c in enumerate(chars))
        rows = ["".join(rnd.choice(chars) for _ in range(16)) for _ in range(16)]
        spec = ("palette: free\nlegend:\n" + legend + "frame:\n"
                + "\n".join(f"  {r}" for r in rows) + "\n")
        _, warns = self._analyze(spec)
        self.assertFalse(any("join breaks" in w for w in warns))

    def test_sprites_are_not_seam_checked(self):
        # A sprite has a transparent margin, not a wrap; there is no seam.
        lines, warns = self._analyze(sprite_spec(filled_box(16, outline="K")))
        self.assertFalse(any("seam:" in ln for ln in lines))
        self.assertFalse(any("join breaks" in w for w in warns))

    def test_only_blocks_are_seam_checked(self):
        # The same broken gradient: a block repeats against itself so the join
        # matters; a cap is a single face and a UI plate never tiles at all.
        broken = gradient_spec("h")
        _, warns = self._analyze("kind: block\n" + broken)
        self.assertTrue(any("join breaks" in w for w in warns))
        for kind in ("cap", "ui", "icon"):
            lines, warns = self._analyze(f"kind: {kind}\n" + broken)
            self.assertFalse(any("join breaks" in w for w in warns), kind)
            self.assertFalse(any("seam:" in ln for ln in lines), kind)

    def test_ui_is_exempt_from_the_flat_fill_check(self):
        # A 9-slice frame's flat centre is the design, not a missing ramp.
        flat = sprite_spec(["E" * 32] * 32)
        _, warns = self._analyze("kind: block\n" + flat)
        self.assertTrue(any("flat fill" in w for w in warns))
        _, warns = self._analyze("kind: ui\n" + flat)
        self.assertFalse(any("flat fill" in w for w in warns))

    def test_icon_is_exempt_from_the_outline_check(self):
        # Store art is never composited over an unknown HUD background.
        unoutlined = sprite_spec(filled_box(16))
        _, warns = self._analyze("kind: sprite\n" + unoutlined)
        self.assertTrue(any("silhouette edge" in w for w in warns))
        _, warns = self._analyze("kind: icon\n" + unoutlined)
        self.assertFalse(any("silhouette edge" in w for w in warns))

    def test_undeclared_specs_still_get_the_flat_check(self):
        # An unknown kind must not mean unchecked; flat holds for everything
        # except ui, and the warning names that escape hatch.
        mixed = ["g" * 32] * 31 + ["g" * 31 + "."]
        spec = ("legend:\n  . transparent\n  g gold\nframe:\n"
                + "\n".join(f"  {r}" for r in mixed) + "\n")
        _, warns, notes = analyze_spec(spec)
        self.assertTrue(any("flat fill" in w for w in warns))
        self.assertTrue(any("kind: ui" in w for w in warns))
        self.assertTrue(any("could not be inferred" in n for n in notes))

    def test_unknown_kind_is_rejected(self):
        with self.assertRaises(glyph.SpecError) as cm:
            glyph.parse_spec("kind: banner\nlegend:\n  g gold\nframe:\n  g\n")
        self.assertIn("kind:", str(cm.exception))

    def test_animated_block_checks_every_frame(self):
        # Frame 1 tiles; frame 2 is a ramp that does not wrap. Legend chars are
        # distinct from the ramp's a..p so nothing is redefined.
        legend = "".join(f"  {chr(97 + i)} #{20 + i * 14:02x}{20 + i * 14:02x}"
                         f"{20 + i * 14:02x}\n" for i in range(16))
        good = "\n".join("  " + "az" * 8 for _ in range(16))
        bad = "\n".join("  " + "".join(chr(97 + x) for x in range(16))
                        for _ in range(16))
        spec = ("palette: free\nframetime: 4\nlegend:\n" + legend
                + "  z bone\n" + f"frame:\n{good}\nframe:\n{bad}\n")
        _, warns = self._analyze(spec)
        self.assertTrue(any("left/right join breaks" in w for w in warns),
                        "a seam in a later frame must still be caught")

    def test_duplicate_legend_key_is_rejected(self):
        # A silent overwrite repaints every cell using that char; it is exactly
        # the kind of mistake that produces plausible-looking wrong art.
        with self.assertRaises(glyph.SpecError) as cm:
            glyph.parse_spec("legend:\n  g gold\n  g ink\nframe:\n  gg\n  gg\n")
        self.assertIn("already defined", str(cm.exception))

    def test_roll_half_centres_both_wrap_edges(self):
        size = 4
        px = [(x * 10, y * 10, 0, 255) for y in range(size) for x in range(size)]
        rolled = glyph.roll_half(px, size)
        # The pixel that was at the wrap corner (size-1, size-1) lands one step
        # up-left of centre, putting both joins through the middle.
        self.assertEqual(rolled[1 * size + 1], px[(size - 1) * size + (size - 1)])
        self.assertEqual(len(rolled), len(px))
        self.assertEqual(sorted(rolled), sorted(px))  # a roll moves, never adds

    def test_seam_preview_is_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = pathlib.Path(tmp)
            spec = d / "b.glyph"
            spec.write_text("legend:\n  K ink\n  b bone\nframe:\n"
                            + "\n".join("  " + "Kb" * 8 for _ in range(16)) + "\n")
            rc, out, _ = run_main([str(spec), "-o", str(d / "b.png"),
                                   "--tile-preview", "--no-preview"])
            self.assertEqual(rc, 0)
            self.assertTrue((d / "b@seam.png").exists())
            self.assertTrue((d / "b@2x2.png").exists())
            self.assertEqual(png_size(d / "b@seam.png"), (256, 256))
            self.assertIn("seam-centred", out)


class PaletteWarningTests(unittest.TestCase):
    def _warn(self, spec):
        # Raw hex is advisory, so these assertions read the note tier.
        _, _, notes = analyze_spec(spec)
        return notes

    def test_raw_hex_warns(self):
        notes = self._warn("legend:\n  a #ff00ff\n  b #00ff00\nframe:\n  ab\n  ba\n")
        self.assertTrue(any("raw hex" in n for n in notes))
        self.assertTrue(any("--snap-palette" in n for n in notes))

    def test_tokens_and_ramp_steps_are_clean(self):
        warns = self._warn("legend:\n  a gold\n  b gold-1\n  c ink\nframe:\n"
                           "  ab\n  bc\n")
        self.assertFalse(any("raw hex" in w for w in warns))

    def test_palette_free_opts_out(self):
        warns = self._warn("palette: free\nlegend:\n  a #ff00ff\nframe:\n  aa\n  aa\n")
        self.assertFalse(any("raw hex" in w for w in warns))

    def test_palette_directive_is_validated(self):
        with self.assertRaises(glyph.SpecError):
            glyph.parse_spec("palette: whatever\nlegend:\n  a gold\nframe:\n  a\n")

    def test_edge_and_frames_directives_are_validated(self):
        for bad in ("edge: whatever\n", "frames: sideways\n",
                    "downscale: bicubic\n"):
            with self.assertRaises(glyph.SpecError, msg=bad):
                glyph.parse_spec(bad + "legend:\n  a gold\nframe:\n  a\n")
        _, _, _, meta, _ = glyph.parse_spec(
            "edge: shaped\nframes: split\ndownscale: lanczos\n"
            "legend:\n  a gold\nframe:\n  a\n")
        self.assertEqual(meta["edge"], "shaped")
        self.assertEqual(meta["frames"], "split")
        self.assertEqual(meta["downscale"], "lanczos")

    def test_frames_directive_is_not_confused_with_frametime(self):
        _, _, _, meta, _ = glyph.parse_spec(
            "frametime: 3\nlegend:\n  a gold\nframe:\n  a\n")
        self.assertEqual(meta["frametime"], 3)
        self.assertNotIn("frames", meta)

    def test_directive_values_ignore_trailing_comments(self):
        # Header values are free text, so a '# note' after one must not become
        # part of the value.
        _, _, _, meta, _ = glyph.parse_spec(
            "palette: free   # hand-painted\n"
            "ships: out/a.png   # the shipped master\n"
            "ships: out/b.png 32  # the ladder tier\n"
            "legend:\n  a gold\nframe:\n  a\n")
        self.assertEqual(meta["palette"], "free")
        self.assertEqual(meta["ships"], [("out/a.png", None), ("out/b.png", 32)])

    def test_transcription_is_born_opted_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = pathlib.Path(tmp)
            glyph.write_png(d / "m.png", [(1, 2, 3, 255)] * 4, 2, 2)
            glyph.transcribe_png(d / "m.png", d / "m.glyph")
            _, _, _, meta, _ = glyph.parse_spec((d / "m.glyph").read_text())
            self.assertEqual(meta["palette"], "free")

    def test_shipped_examples_are_palette_clean(self):
        examples = ROOT / ".ai" / "skills" / "mc-textures" / "examples"
        for spec in sorted(examples.glob("*.glyph")):
            warns = self._warn(spec.read_text())
            self.assertFalse(any("raw hex" in w for w in warns),
                             f"{spec.name}: {warns}")


class PreviewSizingTests(unittest.TestCase):
    def test_default_factor_is_capped_to_a_target_size(self):
        # A fixed ×16 turns a 128px master into a 2048px preview that carries
        # nothing the 512px one doesn't.
        for size, want in ((16, 16), (32, 16), (64, 8), (128, 4), (256, 2)):
            self.assertEqual(glyph.preview_factor(size, None), want, f"size {size}")
            self.assertLessEqual(size * glyph.preview_factor(size, None),
                                 glyph.PREVIEW_MAX_PX)

    def test_explicit_scale_is_honoured(self):
        self.assertEqual(glyph.preview_factor(128, 16), 16)
        self.assertEqual(glyph.preview_factor(16, 2), 2)

    def test_ascii_dump_is_skipped_for_large_grids(self):
        px = [(0, 0, 0, 255)] * (128 * 128)
        out = glyph.render_ascii(px, 128, 128)
        self.assertEqual(len(out.splitlines()), 1)
        self.assertIn("skipped", out)
        small = glyph.render_ascii([(0, 0, 0, 255)] * 16, 4, 4)
        self.assertEqual(len(small.splitlines()), 4)

    def test_render_names_the_preview_by_its_actual_factor(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = pathlib.Path(tmp)
            rows = ["g" * 128] * 128
            spec = d / "big.glyph"
            spec.write_text("palette: free\nlegend:\n  g #ffd700\nframe:\n"
                            + "\n".join(f"  {r}" for r in rows) + "\n")
            rc, out, _ = run_main([str(spec), "-o", str(d / "big.png")])
            self.assertEqual(rc, 0)
            self.assertEqual(png_size(d / "big@4x.png"), (512, 512))
            self.assertIn("silhouette dump skipped", out)


class SnapPaletteTests(unittest.TestCase):
    def test_every_suggestion_parses_back_to_itself(self):
        # A suggestion the legend parser rejects is worse than no suggestion,
        # and one that resolves to a different colour is a trap.
        for token, hex_ in glyph.NAMED_COLORS.items():
            base = glyph.parse_color(hex_)
            for step in range(-glyph.RAMP_MAX_STEP, glyph.RAMP_MAX_STEP + 1):
                name = token if step == 0 else f"{token}{step:+d}"
                want = glyph.shade(base, step) if step else base
                self.assertEqual(glyph.parse_color(name), want, name)

    def test_exact_palette_colour_snaps_to_its_token(self):
        name, dist, _ = glyph.nearest_token(glyph.parse_color("#50c878"))
        self.assertEqual(name, "mercantile.emerald")
        self.assertEqual(dist, 0.0)

    def test_a_shared_metal_snaps_to_the_metal_not_a_brand(self):
        # Three tokens hold #ffd700. A raw gold in an arbitrary mod's spec is
        # almost never a claim on Meridian's or Prosperity's identity, so the
        # suggestion that keeps the spec conformant is the shared tone.
        for hex_, want in (("#ffd700", "metal.gold"),
                           ("#daa520", "metal.gold-deep")):
            name, dist, _ = glyph.nearest_token(glyph.parse_color(hex_))
            self.assertEqual(name, want)
            self.assertEqual(dist, 0.0)

    def test_a_hand_mixed_shadow_finds_a_ramp_step(self):
        # The exact case that motivated ramp steps: a manual emerald shadow.
        name, dist, _ = glyph.nearest_token(glyph.parse_color("#2c8a57"))
        self.assertTrue(name.startswith("mercantile.emerald"), name)
        self.assertIn("-", name)          # a shadow step, not the base tone
        self.assertLess(dist, glyph.SNAP_LIMIT)

    def test_off_palette_colour_is_reported_as_such(self):
        lines = glyph.snap_palette([("x", "#ff00ff")])
        self.assertTrue(any("genuinely off-palette" in ln for ln in lines))

    def test_report_marks_close_and_distant_differently(self):
        emerald = glyph.NAMED_COLORS["mercantile.emerald"]
        lines = glyph.snap_palette([("a", emerald), ("b", "#2c8a57")])
        self.assertTrue(any("identical" in ln for ln in lines))
        self.assertTrue(any("your call" in ln or "indistinguishable" in ln
                            for ln in lines))

    def test_cli_reports_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = pathlib.Path(tmp)
            spec = d / "s.glyph"
            spec.write_text("legend:\n  . transparent\n  d #2c8a57\n"
                            "frame:\n  .d\n  d.\n")
            rc, out, _ = run_main([str(spec), "--snap-palette"])
            self.assertEqual(rc, 0)
            self.assertIn("mercantile.emerald", out)
            self.assertIn("Suggestions only", out)
            self.assertFalse((d / "s.png").exists())

    def test_list_colors_groups_the_palette_by_owner(self):
        # DESIGN-SYSTEM.md §8 and the skill both send authors here to learn the
        # palette, so this output has to teach the rule the renderer enforces.
        rc, out, _ = run_main(["--list-colors"])
        self.assertEqual(rc, 0)
        for heading in ("shared neutrals", "shared material tones",
                        "per-mod accents", "bare aliases"):
            self.assertIn(heading, out)
        self.assertIn("crimson", out)
        self.assertTrue(any(ln.split() == ["crimson", "#dc143c", "=", "tribulation"]
                            for ln in out.splitlines()), out)
        self.assertTrue(any(ln.startswith("    gold ")
                            and ln.endswith("= shared material tone")
                            for ln in out.splitlines()), out)

    def test_cli_says_so_when_nothing_to_snap(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = pathlib.Path(tmp)
            spec = d / "s.glyph"
            spec.write_text(STATIC_SPEC)
            rc, out, _ = run_main([str(spec), "--snap-palette"])
            self.assertEqual(rc, 0)
            self.assertIn("already on design-system tokens", out)


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _spec(self, content, name="v.glyph"):
        p = self.dir / name
        p.write_text(content)
        return p

    def test_clean_render_verifies(self):
        spec = self._spec(STATIC_SPEC)
        out = self.dir / "v.png"
        run_main([str(spec), "-o", str(out), "--no-preview"])
        rc, out_text, _ = run_main([str(spec), "-o", str(out), "--verify"])
        self.assertEqual(rc, 0)
        self.assertIn("pixel-identical", out_text)

    def test_hand_patched_pixel_is_drift(self):
        spec = self._spec(STATIC_SPEC)
        out = self.dir / "v.png"
        run_main([str(spec), "-o", str(out), "--no-preview"])
        px, w, h = glyph.read_png(out)
        px[5] = (255, 0, 0, 255)
        glyph.write_png(out, px, w, h)
        rc, _, err = run_main([str(spec), "-o", str(out), "--verify"])
        self.assertEqual(rc, 1)
        self.assertIn("1 of 16 pixels differ", err)
        self.assertIn("(first at 1,1)", err)

    def test_missing_shipped_master_is_drift(self):
        spec = self._spec(STATIC_SPEC)
        rc, _, err = run_main([str(spec), "-o", str(self.dir / "gone.png"), "--verify"])
        self.assertEqual(rc, 1)
        self.assertIn("missing", err)

    def test_verify_writes_nothing(self):
        spec = self._spec(STATIC_SPEC)
        out = self.dir / "v.png"
        run_main([str(spec), "-o", str(out), "--verify"])
        self.assertFalse(out.exists())

    def test_verify_without_a_target_fails_rather_than_guessing(self):
        spec = self._spec(STATIC_SPEC)
        rc, _, err = run_main([str(spec), "--verify"])
        self.assertEqual(rc, 1)
        self.assertIn("no 'ships:' target", err)

    def test_ships_directive_locates_every_tier(self):
        shipped = self.dir / "assets" / "coin.png"
        ladder = self.dir / "assets" / "coin-16.png"
        spec = self._spec(f"ships: {shipped}\nships: {ladder} 16\n" + STATIC_SPEC)
        run_main([str(spec), "-o", str(shipped), "--no-preview"])
        rc, _, err = run_main([str(spec), "--verify"])
        self.assertEqual(rc, 1)          # the 16px tier hasn't shipped yet
        self.assertIn("coin-16.png", err)
        run_main([str(spec), "-o", str(ladder), "--scale-to", "16"])
        rc, out, err = run_main([str(spec), "--verify"])
        self.assertEqual(rc, 0, err)
        self.assertIn("coin-16.png", out)

    def test_resized_shipped_master_is_drift(self):
        spec = self._spec(STATIC_SPEC)
        out = self.dir / "v.png"
        glyph.write_png(out, [(0, 0, 0, 0)] * 64, 8, 8)
        rc, _, err = run_main([str(spec), "-o", str(out), "--verify"])
        self.assertEqual(rc, 1)
        self.assertIn("is 8×8, the spec renders 4×4", err)

    def test_animated_verify_covers_mcmeta(self):
        spec = self._spec(ANIM_SPEC, "a.glyph")
        out = self.dir / "a.png"
        run_main([str(spec), "-o", str(out), "--no-preview"])
        rc, _, _ = run_main([str(spec), "-o", str(out), "--verify"])
        self.assertEqual(rc, 0)
        meta = self.dir / "a.png.mcmeta"
        meta.write_text(json.dumps({"animation": {"frametime": 99, "interpolate": False}}))
        rc, _, err = run_main([str(spec), "-o", str(out), "--verify"])
        self.assertEqual(rc, 1)
        self.assertIn("frametime", err)

    def test_split_frames_and_scale_to_verify(self):
        spec = self._spec(ANIM_SPEC, "a.glyph")
        out = self.dir / "a.png"
        run_main([str(spec), "-o", str(out), "--split-frames", "--no-preview"])
        rc, _, _ = run_main([str(spec), "-o", str(out), "--split-frames", "--verify"])
        self.assertEqual(rc, 0)
        st = self._spec(STATIC_SPEC)
        big = self.dir / "big.png"
        run_main([str(st), "-o", str(big), "--scale-to", "16"])
        rc, _, _ = run_main([str(st), "-o", str(big), "--scale-to", "16", "--verify"])
        self.assertEqual(rc, 0)

    def _run_on_stdin(self, spec_text, argv):
        stdin, sys.stdin = sys.stdin, io.StringIO(spec_text)
        try:
            return run_main(argv)
        finally:
            sys.stdin = stdin

    def test_verify_reads_a_spec_from_stdin(self):
        # A spec on stdin has no path to re-open, so verification has to work
        # from what was already parsed. Getting this wrong raised an uncaught
        # FileNotFoundError out of a script that reports every other failure as
        # a message and an exit code.
        out = self.dir / "s.png"
        run_main([str(self._spec(STATIC_SPEC)), "-o", str(out), "--no-preview"])
        rc, stdout, stderr = self._run_on_stdin(
            STATIC_SPEC, ["-", "--verify", "-o", str(out)])
        self.assertEqual(rc, 0, stderr)
        self.assertIn("pixel-identical", stdout)

    def test_verify_from_stdin_reports_drift_not_a_traceback(self):
        out = self.dir / "s.png"
        run_main([str(self._spec(STATIC_SPEC)), "-o", str(out), "--no-preview"])
        px, w, h = glyph.read_png(out)
        px[5] = (255, 0, 255, 255)
        glyph.write_png(out, px, w, h)
        rc, _, stderr = self._run_on_stdin(
            STATIC_SPEC, ["-", "--verify", "-o", str(out)])
        self.assertEqual(rc, 1)
        self.assertIn("pixels differ", stderr)

    def test_verify_from_stdin_without_a_target_is_a_clean_error(self):
        rc, _, stderr = self._run_on_stdin(STATIC_SPEC, ["-", "--verify"])
        self.assertEqual(rc, 1)
        self.assertIn("no 'ships:' target", stderr)

    def test_verify_all_walks_a_tree(self):
        # This is the member-facing entry point: the renderer is vendored into
        # every member repo, so the repo-wide walk has to live in it rather
        # than in a concord-only script.
        art = self.dir / "art" / "glyphs"
        art.mkdir(parents=True)
        shipped = self.dir / "assets" / "coin.png"
        linked = art / "coin.glyph"
        linked.write_text(f"ships: {shipped}\n" + STATIC_SPEC)
        (art / "loose.glyph").write_text(STATIC_SPEC)      # declares no target
        run_main([str(linked), "-o", str(shipped), "--no-preview"])

        rc, out, _ = run_main(["--verify-all", str(art), "-v"])
        self.assertEqual(rc, 0)
        self.assertIn("1 verified, 0 drifted, 0 malformed, 0 blocked, 1 unlinked", out)
        self.assertIn("unlinked", out)

        px, w, h = glyph.read_png(shipped)
        px[5] = (255, 0, 255, 255)
        glyph.write_png(shipped, px, w, h)
        rc, out, _ = run_main(["--verify-all", str(art)])
        self.assertEqual(rc, 1)
        self.assertIn("DRIFT", out)
        self.assertIn("1 verified, 1 drifted, 0 malformed, 0 blocked, 1 unlinked", out)

    def test_verify_all_walks_subdirectories(self):
        # A repo with enough art to sort it into folders is the repo that most
        # needs the check: a walk that stopped at the top level would report a
        # confident green over art it never opened.
        art = self.dir / "art" / "glyphs"
        (art / "hud" / "pips").mkdir(parents=True)
        shipped = self.dir / "assets" / "deep.png"
        nested = art / "hud" / "pips" / "deep.glyph"
        nested.write_text(f"ships: {shipped}\n" + STATIC_SPEC)
        run_main([str(nested), "-o", str(shipped), "--no-preview"])

        rc, out, _ = run_main(["--verify-all", str(art), "-v"])
        self.assertEqual(rc, 0)
        self.assertIn("1 verified", out)
        self.assertIn("deep.glyph", out)

        px, w, h = glyph.read_png(shipped)
        px[5] = (255, 0, 255, 255)
        glyph.write_png(shipped, px, w, h)
        rc, out, _ = run_main(["--verify-all", str(art)])
        self.assertEqual(rc, 1)
        self.assertIn("DRIFT", out)

    def test_a_malformed_spec_is_not_reported_as_drift(self):
        # A wrapper can only word its error honestly if the two are apart: one
        # says the shipped art was edited, the other says the spec won't parse.
        art = self.dir / "art" / "glyphs"
        art.mkdir(parents=True)
        (art / "bad.glyph").write_text(
            f"ships: {self.dir / 'assets' / 'bad.png'}\n"
            "legend:\n  g gold\nframe:\n  gg\n  g\n")   # ragged grid
        rc, out, _ = run_main(["--verify-all", str(art)])
        self.assertEqual(rc, 1)
        self.assertIn("BROKEN", out)
        self.assertNotIn("DRIFT", out)
        self.assertIn("0 verified, 0 drifted, 1 malformed, 0 blocked, 0 unlinked", out)

    def test_split_frame_specs_declare_their_packaging(self):
        # concord#47: the packaging is a property of the spec, so --verify-all,
        # which has no flags to pass, has to be able to read it off the spec.
        art = self.dir / "art" / "glyphs"
        art.mkdir(parents=True)
        out = self.dir / "assets" / "spark.png"
        spec = art / "spark.glyph"
        spec.write_text(f"frames: split\nships: {out}\n" + ANIM_SPEC)
        rc, _, err = run_main([str(spec), "-o", str(out), "--no-preview"])
        self.assertEqual(rc, 0, err)
        self.assertTrue((self.dir / "assets" / "spark_0.png").exists())
        self.assertFalse((self.dir / "assets" / "spark.png.mcmeta").exists())

        rc, text, _ = run_main(["--verify-all", str(art), "-v"])
        self.assertEqual(rc, 0)
        self.assertIn("spark_1.png", text)

    def test_split_frames_on_a_static_spec_is_a_spec_error_not_drift(self):
        art = self.dir / "art" / "glyphs"
        art.mkdir(parents=True)
        (art / "still.glyph").write_text(
            f"frames: split\nships: {self.dir / 'assets' / 'still.png'}\n"
            + STATIC_SPEC)
        rc, out, _ = run_main(["--verify-all", str(art)])
        self.assertEqual(rc, 1)
        self.assertIn("BROKEN", out)
        self.assertIn("2+ frames", out)

    def test_ships_declares_downscaled_tiers_too(self):
        # The mod-icon ladder runs downward: one 512 master, derived 256 and
        # 128 copies. Every tier is named by the spec, so every tier verifies.
        small = self.dir / "assets" / "icon-8.png"
        spec = self._spec(f"ships: {small} 8\n" + _BIG_SPEC, "icon.glyph")
        rc, _, err = run_main([str(spec), "--verify"])
        self.assertEqual(rc, 1)          # the 8px tier hasn't shipped yet
        run_main([str(spec), "-o", str(small), "--scale-to", "8"])
        rc, out, err = run_main([str(spec), "--verify"])
        self.assertEqual(rc, 0, err)
        self.assertIn("icon-8.png", out)

    def test_an_upscaled_tier_must_be_a_whole_multiple(self):
        spec = self._spec(f"ships: {self.dir / 'x.png'} 10\n" + STATIC_SPEC)
        rc, _, err = run_main([str(spec), "--verify"])
        self.assertEqual(rc, 1)
        self.assertIn("whole multiple", err)

    @unittest.skipIf(glyph.magick_binary() is None, "ImageMagick not installed")
    def test_a_ratio_that_is_no_whole_factor_resamples_through_magick(self):
        # 4 -> 3 has no integer factor, so the built-in average can't express
        # it; ImageMagick can, and the tier verifies against what it produced.
        odd = self.dir / "assets" / "odd.png"
        spec = self._spec(f"ships: {odd} 3\n" + STATIC_SPEC)
        rc, out, err = run_main([str(spec), "-o", str(odd), "--scale-to", "3"])
        self.assertEqual(rc, 0, err)
        self.assertIn("ImageMagick box", out)
        self.assertEqual(png_size(odd), (3, 3))
        rc, _, err = run_main([str(spec), "--verify"])
        self.assertEqual(rc, 0, err)

    @unittest.skipIf(glyph.magick_binary() is None, "ImageMagick not installed")
    def test_a_declared_filter_routes_through_magick_and_verifies(self):
        big = "downscale: lanczos\n" + _BIG_SPEC
        small = self.dir / "assets" / "hero-4.png"
        spec = self._spec(f"ships: {small} 4\n" + big, "hero.glyph")
        rc, out, err = run_main([str(spec), "-o", str(small), "--scale-to", "4"])
        self.assertEqual(rc, 0, err)
        self.assertIn("ImageMagick lanczos", out)
        rc, _, err = run_main([str(spec), "--verify"])
        self.assertEqual(rc, 0, err)
        # ... and it is a different resampling from the built-in average, which
        # is the whole reason for reaching past it.
        box = self.dir / "assets" / "hero-box.png"
        boxed = self._spec(f"ships: {box} 4\n" + big.replace(
            "downscale: lanczos\n", ""), "hero-box.glyph")
        run_main([str(boxed), "-o", str(box), "--scale-to", "4"])
        self.assertNotEqual(glyph.read_png(small)[0], glyph.read_png(box)[0])

    @unittest.skipIf(glyph.magick_binary() is None, "ImageMagick not installed")
    def test_either_imagemagick_name_ships_the_same_bytes(self):
        # v7 is `magick`, v6 is `convert`, and a v7 package often keeps both.
        # They may write different PNG metadata, but the pixels come home and
        # are re-encoded here, so the shipped file cannot depend on which one
        # a given machine happens to have.
        names = [n for n in ("magick", "convert") if shutil.which(n)]
        if len(names) < 2:
            self.skipTest("only one ImageMagick entry point on this machine")
        spec = self._spec("downscale: lanczos\n" + _BIG_SPEC, "hero.glyph")
        written = []
        real = glyph.magick_binary
        try:
            for name in names:
                glyph.magick_binary = (lambda p: (lambda: p))(shutil.which(name))
                out = self.dir / f"via-{name}.png"
                rc, _, err = run_main([str(spec), "-o", str(out), "--scale-to", "4"])
                self.assertEqual(rc, 0, err)
                written.append(out.read_bytes())
        finally:
            glyph.magick_binary = real
        self.assertEqual(written[0], written[1])

    def test_a_convert_that_is_not_imagemagick_is_not_used(self):
        # `convert` is a common name: on Windows it is the filesystem tool.
        # Running that with a resize command would read as ImageMagick
        # misbehaving rather than as ImageMagick being absent.
        impostor = self.dir / "convert"
        impostor.write_text("#!/bin/sh\necho 'File System Conversion Utility'\n")
        impostor.chmod(0o755)
        cached, glyph._MAGICK_LOOKUP[:] = list(glyph._MAGICK_LOOKUP), []
        real_which = shutil.which
        shutil.which = lambda n, *a, **k: str(impostor) if n == "convert" else None
        try:
            self.assertIsNone(glyph.magick_binary())
            with self.assertRaises(glyph.ToolError) as cm:
                glyph.magick_resize([(0, 0, 0, 0)] * 16, 4, 2, "lanczos")
        finally:
            shutil.which = real_which
            glyph._MAGICK_LOOKUP[:] = cached
        self.assertIn("is not ImageMagick", str(cm.exception))

    def test_a_missing_imagemagick_blocks_rather_than_accuses(self):
        # The spec parses and the art may be perfect — what failed is the
        # machine, so this is neither drift nor a malformed spec.
        art = self.dir / "art" / "glyphs"
        art.mkdir(parents=True)
        (art / "hero.glyph").write_text(
            f"downscale: lanczos\nships: {self.dir / 'assets' / 'h.png'} 2\n"
            + STATIC_SPEC)
        real, glyph.magick_binary = glyph.magick_binary, lambda: None
        try:
            rc, out, _ = run_main(["--verify-all", str(art)])
        finally:
            glyph.magick_binary = real
        self.assertEqual(rc, 1)
        self.assertIn("BLOCKED", out)
        self.assertNotIn("DRIFT", out)
        self.assertNotIn("BROKEN", out)
        self.assertIn("ImageMagick is not installed", out)
        self.assertIn("0 verified, 0 drifted, 0 malformed, 1 blocked, 0 unlinked", out)

    def test_verify_all_on_a_missing_directory_is_not_a_failure(self):
        rc, out, _ = run_main(["--verify-all", str(self.dir / "nope")])
        self.assertEqual(rc, 0)
        self.assertIn("no such directory", out)

    def test_shipped_examples_are_reproducible(self):
        # The repeatability rule, applied to the skill's own reference specs.
        examples = ROOT / ".ai" / "skills" / "mc-textures" / "examples"
        for spec in sorted(examples.glob("*.glyph")):
            out = self.dir / f"{spec.stem}.png"
            run_main([str(spec), "-o", str(out), "--no-preview"])
            rc, _, err = run_main([str(spec), "-o", str(out), "--verify"])
            self.assertEqual(rc, 0, f"{spec.name}: {err}")


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
        for bad in ("10", "0", "-4"):
            rc, _, err = run_main([str(spec), "-o", str(self.dir / "t.png"),
                                   "--scale-to", bad])
            self.assertEqual(rc, 1, bad)
            self.assertIn("whole multiple", err)

    def test_scale_to_downscales_an_exact_factor(self):
        # A master that is itself an upscale of a smaller grid downscales back
        # to that grid exactly — which is why the icon ladder can be derived.
        spec = self._spec_file(STATIC_SPEC)
        native = self.dir / "n.png"
        big = self.dir / "big.png"
        small = self.dir / "small.png"
        run_main([str(spec), "-o", str(native), "--no-preview"])
        run_main([str(spec), "-o", str(big), "--scale-to", "16"])
        rc, out, _ = run_main([str(big), "--from-png", "-o", str(self.dir / "big.glyph")])
        self.assertEqual(rc, 0)
        rc, out, _ = run_main([str(self.dir / "big.glyph"), "-o", str(small),
                               "--scale-to", "4"])
        self.assertEqual(rc, 0)
        self.assertIn("area-average ÷4", out)
        self.assertEqual(glyph.read_png(small)[0], glyph.read_png(native)[0])

    def test_box_downscale_weights_colour_by_alpha(self):
        # One opaque gold pixel among three transparent ones averages to gold
        # at a quarter alpha — the transparent side contributes coverage, never
        # colour, so a fading edge doesn't drag black inward.
        gold = glyph.parse_color("gold")
        out, w, h = glyph.scale_box([gold, glyph.TRANSPARENT,
                                     glyph.TRANSPARENT, glyph.TRANSPARENT], 2, 2, 2)
        self.assertEqual((w, h), (1, 1))
        self.assertEqual(out[0][:3], gold[:3])
        self.assertEqual(out[0][3], 64)
        out, _, _ = glyph.scale_box([glyph.TRANSPARENT] * 4, 2, 2, 2)
        self.assertEqual(out, [glyph.TRANSPARENT])

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
