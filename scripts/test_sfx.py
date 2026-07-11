#!/usr/bin/env python3
"""Unit tests for the vendored sound synth (.ai/skills/mc-audio/scripts/sfx.py).

Hermetic: specs are inline dicts, synthesis is checked numerically — no ffmpeg
needed (encode paths are exercised only when ffmpeg is present). Run with:

    python3 -m unittest scripts.test_sfx
    python3 scripts/test_sfx.py
"""

from __future__ import annotations

import importlib.util
import io
import json
import math
import pathlib
import tempfile
import unittest
import wave
from contextlib import redirect_stderr, redirect_stdout

ROOT = pathlib.Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location(
    "sfx", ROOT / ".ai" / "skills" / "mc-audio" / "scripts" / "sfx.py")
sfx = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sfx)


def spec_of(layers, **top):
    base = {"layers": layers}
    base.update(top)
    return sfx.parse_spec(json.dumps(base))


def rms(samples):
    return math.sqrt(sum(x * x for x in samples) / len(samples)) if samples else 0.0


class ParseTests(unittest.TestCase):
    def test_defaults(self):
        spec = spec_of([{"freq": 440}])
        self.assertEqual(spec["sample_rate"], 44100)
        self.assertEqual(spec["peak_dbfs"], -1.0)

    def test_errors(self):
        with self.assertRaises(sfx.SpecError):
            sfx.parse_spec("not json")
        with self.assertRaises(sfx.SpecError):
            sfx.parse_spec("[]")
        with self.assertRaises(sfx.SpecError):
            sfx.parse_spec('{"layers": []}')
        with self.assertRaises(sfx.SpecError):
            spec_of([{"freq": 440}], sample_rate=22050)
        with self.assertRaises(sfx.SpecError):
            spec_of([{"freq": 440}], peak_dbfs=1.0)


class SynthTests(unittest.TestCase):
    def test_duration_inferred(self):
        spec = spec_of([{
            "freq": 440, "duration": 0.5,
            "env": {"attack": 0.0, "decay": 0.0, "sustain": 1.0, "release": 0.1},
        }])
        samples, sr = sfx.synthesize(spec)
        self.assertAlmostEqual(len(samples) / sr, 0.6, places=2)

    def test_repeat_extends(self):
        spec = spec_of([{
            "freq": 440, "duration": 0.1,
            "env": {"attack": 0.0, "decay": 0.0, "sustain": 1.0, "release": 0.0},
            "repeat": {"count": 3, "interval": 0.5},
        }])
        samples, sr = sfx.synthesize(spec)
        self.assertAlmostEqual(len(samples) / sr, 1.1, places=2)

    def test_normalize_hits_target(self):
        spec = spec_of([{"freq": 440, "duration": 0.2, "gain": 0.1}])
        samples, _ = sfx.synthesize(spec)
        normed, _ = sfx.normalize(samples, -1.0)
        peak = max(abs(x) for x in normed)
        self.assertAlmostEqual(peak, 10 ** (-1.0 / 20.0), places=4)

    def test_duty_shifts_square_mean(self):
        flat = {"attack": 0.0, "decay": 0.0, "sustain": 1.0, "release": 0.0}
        wide = spec_of([{"waveform": "square", "freq": 100, "duration": 0.5, "env": flat}])
        thin = spec_of([{"waveform": "square", "freq": 100, "duration": 0.5,
                         "duty": 0.25, "env": flat}])
        mean_wide = sum(sfx.synthesize(wide)[0]) / (0.5 * 44100)
        mean_thin = sum(sfx.synthesize(thin)[0]) / (0.5 * 44100)
        self.assertAlmostEqual(mean_wide, 0.0, places=1)
        self.assertAlmostEqual(mean_thin, -0.5, places=1)

    def test_vibrato_changes_output(self):
        base = [{"freq": 440, "duration": 0.2}]
        with_vib = [{"freq": 440, "duration": 0.2,
                     "vibrato": {"rate": 8, "depth": 1.0}}]
        a, _ = sfx.synthesize(spec_of(base))
        b, _ = sfx.synthesize(spec_of(with_vib))
        self.assertNotEqual(a, b)

    def test_cutoff_sweep_opens_over_time(self):
        flat = {"attack": 0.0, "decay": 0.0, "sustain": 1.0, "release": 0.0}
        spec = spec_of([{
            "waveform": "noise", "duration": 1.0, "env": flat,
            "filter": {"type": "lowpass", "from": 100, "to": 8000},
        }], seed=1)
        samples, sr = sfx.synthesize(spec)
        half = len(samples) // 2
        self.assertGreater(rms(samples[half:]), 2 * rms(samples[:half]))

    def test_notes_sequence_offsets(self):
        flat = {"attack": 0.0, "decay": 0.0, "sustain": 1.0, "release": 0.0}
        spec = spec_of([{
            "waveform": "sine", "env": flat,
            "notes": [
                {"freq": 440, "start": 0.0, "duration": 0.1},
                {"freq": 660, "start": 0.3, "duration": 0.1},
            ],
        }])
        samples, sr = sfx.synthesize(spec)
        self.assertAlmostEqual(len(samples) / sr, 0.4, places=2)
        gap = samples[int(0.15 * sr):int(0.25 * sr)]
        self.assertEqual(rms(gap), 0.0)  # silence between the notes


class StatsTests(unittest.TestCase):
    def test_silence_measured(self):
        sr = 44100
        tone = [math.sin(2 * math.pi * 440 * i / sr) for i in range(sr // 10)]
        samples = [0.0] * (sr // 20) + tone + [0.0] * (sr // 5)
        stats = sfx.compute_stats(samples, sr)
        self.assertAlmostEqual(stats["lead_silence_s"], 0.05, places=2)
        self.assertAlmostEqual(stats["tail_silence_s"], 0.2, places=2)

    def test_centroid_orders_bright_vs_dark(self):
        sr = 44100
        lo = [math.sin(2 * math.pi * 200 * i / sr) for i in range(sr // 2)]
        hi = [math.sin(2 * math.pi * 6000 * i / sr) for i in range(sr // 2)]
        self.assertLess(sfx.compute_stats(lo, sr)["centroid_hz"],
                        sfx.compute_stats(hi, sr)["centroid_hz"])


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = sfx.main(argv)
        return rc, out.getvalue(), err.getvalue()

    def test_render_writes_outputs(self):
        spec_path = self.dir / "blip.sfx"
        spec_path.write_text(json.dumps({
            "subtitle": "test.subtitle.blip", "seed": 1,
            "layers": [{"freq": 880, "duration": 0.1}],
        }))
        ogg = self.dir / "blip.ogg"
        rc, out, err = self._run([str(spec_path), "-o", str(ogg)])
        self.assertEqual(rc, 0)
        self.assertTrue(ogg.exists() or (self.dir / "blip.wav").exists())
        self.assertTrue((self.dir / "blip.report.png").exists())
        self.assertIn("silence:", out)

    def test_missing_subtitle_warns(self):
        spec_path = self.dir / "s.sfx"
        spec_path.write_text(json.dumps({"layers": [{"freq": 440, "duration": 0.05}]}))
        rc, _, err = self._run([str(spec_path), "-o", str(self.dir / "s.ogg"), "--no-report"])
        self.assertEqual(rc, 0)
        self.assertIn("MISSING", err)

    def test_long_cue_warns(self):
        spec_path = self.dir / "l.sfx"
        spec_path.write_text(json.dumps({
            "subtitle": "t.s.l",
            "layers": [{"freq": 100, "duration": 3.0}],
        }))
        rc, _, err = self._run([str(spec_path), "-o", str(self.dir / "l.ogg"), "--no-report"])
        self.assertEqual(rc, 0)
        self.assertIn("long for an SFX cue", err)

    def test_bad_spec_is_reported(self):
        spec_path = self.dir / "bad.sfx"
        spec_path.write_text("{}")
        rc, _, err = self._run([str(spec_path)])
        self.assertEqual(rc, 2)
        self.assertIn("layers", err)

    def test_wav_is_mono_16bit(self):
        samples = [0.5, -0.5] * 100
        path = self.dir / "t.wav"
        sfx.write_wav(path, samples, 44100)
        with wave.open(str(path), "rb") as w:
            self.assertEqual(w.getnchannels(), 1)
            self.assertEqual(w.getsampwidth(), 2)
            self.assertEqual(w.getframerate(), 44100)
            self.assertEqual(w.getnframes(), 200)

    def test_shipped_examples_render(self):
        examples = ROOT / ".ai" / "skills" / "mc-audio" / "examples"
        for spec in sorted(examples.glob("*.sfx")):
            rc, out, err = self._run(
                [str(spec), "-o", str(self.dir / f"{spec.stem}.ogg"), "--no-report"])
            self.assertEqual(rc, 0, f"{spec.name}: {err}")
            self.assertNotIn("warning", err, f"{spec.name} trips a quality warning: {err}")


if __name__ == "__main__":
    unittest.main()
