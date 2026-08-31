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
import shutil
import struct
import tempfile
import unittest
import wave
from contextlib import redirect_stderr, redirect_stdout

HAVE_FFMPEG = shutil.which("ffmpeg") is not None

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


def alias_share(module, freq, waveform, sr=44100):
    """Fraction of spectral energy sitting away from the true harmonics.

    A naive square/saw folds its above-Nyquist harmonics back down as
    inharmonic partials; this measures how much of the sound that junk is.
    """
    spec = spec_of([{"waveform": waveform, "freq": freq, "duration": 0.4,
                     "env": {"attack": 0.01, "decay": 0, "sustain": 1.0,
                             "release": 0.01}}])
    buf, _ = module.synthesize(spec)
    frames = module._stft(buf[5000:5000 + 1024 * 8])
    avg = [sum(f[k] for f in frames) / len(frames) for k in range(len(frames[0]))]
    harmonics = {round(h * freq * 1024 / sr) for h in range(1, int(sr / 2 / freq) + 1)}
    off = sum(v for k, v in enumerate(avg)
              if not any(abs(k - b) <= 2 for b in harmonics))
    return off / sum(avg)


class BandLimitTests(unittest.TestCase):
    def test_polyblep_suppresses_fold_back(self):
        naive = sfx._poly_blep
        try:
            for waveform in ("saw", "square"):
                for freq in (2000, 5000, 8000):
                    sfx._poly_blep = lambda t, dt: 0.0
                    before = alias_share(sfx, freq, waveform)
                    sfx._poly_blep = naive
                    after = alias_share(sfx, freq, waveform)
                    self.assertLess(after, before / 2.5,
                                    f"{waveform} @{freq} Hz: {before:.3f} -> {after:.3f}")
        finally:
            sfx._poly_blep = naive

    def test_shape_and_duty_survive_band_limiting(self):
        # The correction must not alter the waveform's DC level: a 25% duty
        # square still averages -0.5, which is what makes thin duties read thin.
        flat = {"attack": 0.0, "decay": 0.0, "sustain": 1.0, "release": 0.0}
        thin = spec_of([{"waveform": "square", "freq": 100, "duration": 0.5,
                         "duty": 0.25, "env": flat}])
        self.assertAlmostEqual(sum(sfx.synthesize(thin)[0]) / (0.5 * 44100), -0.5, places=1)

    def test_low_frequency_shape_barely_moves(self):
        # At 100 Hz there is almost nothing to band-limit; the correction should
        # stay a correction rather than reshaping the tone.
        flat = {"attack": 0.0, "decay": 0.0, "sustain": 1.0, "release": 0.0}
        spec = spec_of([{"waveform": "saw", "freq": 100, "duration": 0.1, "env": flat}])
        buf, _ = sfx.synthesize(spec)
        self.assertLess(max(abs(x) for x in buf), 1.05)

    def test_sine_is_untouched(self):
        # Sine has no discontinuity to correct, so the band-limiting path must
        # not touch it at any phase increment.
        for phase in (0.0, 1.0, 2.5, 6.0):
            self.assertEqual(sfx._osc("sine", phase, None, 0.5, 0.2),
                             math.sin(phase))
            self.assertEqual(sfx._osc("sine", phase, None, 0.5, 0.0),
                             math.sin(phase))


class LoudnessTests(unittest.TestCase):
    def test_k_weighting_matches_published_48k_table(self):
        # BS.1770 publishes coefficients only for 48 kHz; deriving them there is
        # what proves the derivation is right at 44.1 kHz too.
        shelf_b, shelf_a, hp_b, hp_a = sfx.k_weighting_coeffs(48000)
        expected = (
            [1.53512485958697, -2.69169618940638, 1.19839281085285],
            [1.0, -1.69065929318241, 0.73248077421585],
            [1.0, -2.0, 1.0],
            [1.0, -1.99004745483398, 0.99007225036621],
        )
        for got, want in zip((shelf_b, shelf_a, hp_b, hp_a), expected):
            for a, b in zip(got, want):
                self.assertAlmostEqual(a, b, places=10)

    def test_loudness_orders_dense_above_sparse(self):
        sr = 44100
        square = [1.0 if (i // 50) % 2 else -1.0 for i in range(sr // 2)]
        sine = [math.sin(2 * math.pi * 441 * i / sr) for i in range(sr // 2)]
        self.assertGreater(sfx.measure_loudness(square, sr),
                           sfx.measure_loudness(sine, sr))

    def test_normalize_loudness_hits_target(self):
        sr = 44100
        for wave_fn in (lambda i: math.sin(2 * math.pi * 440 * i / sr),
                        lambda i: 1.0 if (i // 50) % 2 else -1.0):
            samples = [0.3 * wave_fn(i) for i in range(sr // 2)]
            out, _, _, limited = sfx.normalize_loudness(samples, sr, -14.0, -1.0)
            self.assertEqual(limited, 0.0)
            self.assertAlmostEqual(sfx.measure_loudness(out, sr), -14.0, places=2)

    def test_peak_ceiling_wins_over_target(self):
        # A lone spike can't reach the target without clipping; the ceiling must
        # hold and the shortfall must be reported rather than silently clipped.
        sr = 44100
        samples = [0.0] * sr
        samples[10] = 1.0
        out, _, _, limited = sfx.normalize_loudness(samples, sr, -14.0, -1.0)
        self.assertGreater(limited, 1.0)
        self.assertLessEqual(max(abs(x) for x in out), 10 ** (-1.0 / 20.0) + 1e-9)

    def test_examples_land_on_one_loudness(self):
        # The point of the change: cues that used to span ~10 dB now match.
        examples = ROOT / ".ai" / "skills" / "mc-audio" / "examples"
        measured = []
        for path in sorted(examples.glob("*.sfx")):
            spec = sfx.parse_spec(path.read_text())
            buf, sr = sfx.synthesize(spec)
            buf, _, _, _ = sfx.normalize_loudness(
                buf, sr, spec["loudness_lufs"], spec["peak_dbfs"])
            measured.append(sfx.measure_loudness(buf, sr))
        self.assertLess(max(measured) - min(measured), 0.5)

    def test_loudness_can_be_opted_out(self):
        spec = spec_of([{"freq": 440}], loudness_lufs=None)
        self.assertIsNone(spec["loudness_lufs"])
        with self.assertRaises(sfx.SpecError):
            spec_of([{"freq": 440}], loudness_lufs=3.0)


class SeedIsolationTests(unittest.TestCase):
    NOISE_A = {"waveform": "noise", "duration": 0.05, "start": 0.0}
    NOISE_B = {"waveform": "noise", "duration": 0.05, "start": 0.5}

    def _at(self, layers, seed=7):
        samples, sr = sfx.synthesize(spec_of(layers, seed=seed))
        off = int(0.5 * sr)
        return samples[off:off + 400]

    def test_editing_one_layer_leaves_another_alone(self):
        alone = self._at([self.NOISE_B])
        self.assertEqual(alone, self._at([self.NOISE_A, self.NOISE_B]),
                         "inserting a noise layer re-rolled a later one")
        self.assertEqual(alone, self._at([self.NOISE_B, self.NOISE_A]),
                         "reordering layers re-rolled one of them")
        self.assertEqual(alone, self._at([{"freq": 440, "duration": 0.1},
                                          self.NOISE_B]),
                         "an unrelated tone layer re-rolled a noise layer")

    def test_still_deterministic_and_seed_sensitive(self):
        layers = [self.NOISE_A, self.NOISE_B]
        self.assertEqual(self._at(layers), self._at(layers))
        self.assertNotEqual(self._at(layers), self._at(layers, seed=8))

    def test_repeats_are_not_identical_bursts(self):
        spec = spec_of([{"waveform": "noise", "duration": 0.05,
                         "repeat": {"count": 2, "interval": 0.5}}])
        samples, sr = sfx.synthesize(spec)
        off = int(0.5 * sr)
        self.assertNotEqual(samples[:200], samples[off:off + 200])


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_layer_onsets_include_repeats(self):
        spec = {"layers": [
            {"freq": 440, "start": 0.1},
            {"freq": 220, "start": 0.0, "repeat": {"count": 3, "interval": 0.25}},
        ]}
        self.assertEqual(sfx._layer_onsets(spec), [0.0, 0.1, 0.25, 0.5])

    def test_report_is_a_valid_png_of_the_declared_size(self):
        samples = [math.sin(2 * math.pi * 440 * i / 44100) for i in range(4410)]
        stats = sfx.compute_stats(samples, 44100)
        path = self.dir / "r.png"
        sfx.write_report(path, samples, 44100, stats,
                         {"layers": [{"freq": 440, "start": 0.05}]})
        data = path.read_bytes()
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        w, h = struct.unpack(">II", data[16:24])
        self.assertEqual((w, h), (900, 576))

    def test_report_survives_a_silent_and_a_tiny_cue(self):
        for samples in ([0.0] * 2048, [0.1, -0.1]):
            stats = sfx.compute_stats(samples, 44100)
            sfx.write_report(self.dir / "e.png", samples, 44100, stats, None)
            self.assertTrue((self.dir / "e.png").exists())

    def test_font_covers_every_character_the_report_draws(self):
        # A missing glyph renders as a blank, which silently mislabels an axis.
        used = set("0123456789.-+: skHzmdBFSLU")
        for freq in sfx._FREQ_TICKS:
            used |= set(f"{freq // 1000}k" if freq >= 1000 else str(freq))
        self.assertEqual(used - set(sfx._FONT), set())


class DCOffsetTests(unittest.TestCase):
    FLAT = {"attack": 0.0, "decay": 0.0, "sustain": 1.0, "release": 0.0}

    def _dc(self, layer):
        samples, sr = sfx.synthesize(spec_of([layer]))
        return sfx.compute_stats(samples, sr)

    def test_symmetric_waveforms_are_centred(self):
        for waveform in ("sine", "triangle", "square"):
            stats = self._dc({"waveform": waveform, "freq": 200,
                              "duration": 0.3, "env": self.FLAT})
            self.assertLess(stats["dc_pct"], 2.0, waveform)

    def test_thin_duty_carries_an_offset(self):
        thin = self._dc({"waveform": "square", "freq": 440, "duty": 0.125,
                         "duration": 0.3, "env": self.FLAT})
        self.assertGreater(thin["dc_pct"], sfx.DC_OFFSET_WARN_PCT)
        self.assertLess(thin["dc_offset"], 0)  # more time low than high

    def test_a_highpass_recentres_it(self):
        # The fix the warning points at has to actually work.
        layer = {"waveform": "square", "freq": 440, "duty": 0.125,
                 "duration": 0.3, "env": self.FLAT}
        self.assertGreater(self._dc(layer)["dc_pct"], sfx.DC_OFFSET_WARN_PCT)
        blocked = dict(layer, filter={"type": "highpass", "cutoff": 20})
        self.assertLess(self._dc(blocked)["dc_pct"], 2.0)

    def test_threshold_clears_the_reference_cues(self):
        # A pulse wave is offset by construction, so the bar has to sit above
        # what the shipped archetypes measure or it flags correct work.
        examples = ROOT / ".ai" / "skills" / "mc-audio" / "examples"
        for path in sorted(examples.glob("*.sfx")):
            spec = sfx.parse_spec(path.read_text())
            buf, sr = sfx.synthesize(spec)
            buf, _, _, _ = sfx.normalize_loudness(
                buf, sr, spec["loudness_lufs"], spec["peak_dbfs"])
            self.assertLess(sfx.compute_stats(buf, sr)["dc_pct"],
                            sfx.DC_OFFSET_WARN_PCT, path.name)


class AnalysisTests(unittest.TestCase):
    def test_dc_offset_does_not_drag_the_centroid(self):
        # A thin-duty square carries a real DC offset. Left in, it dominates
        # bin 0 and pulls the reported centroid toward zero.
        sr = 44100
        tone = [math.sin(2 * math.pi * 3000 * i / sr) for i in range(sr // 4)]
        clean = sfx.compute_stats(tone, sr)["centroid_hz"]
        offset = sfx.compute_stats([x + 0.5 for x in tone], sr)["centroid_hz"]
        self.assertAlmostEqual(clean, offset, delta=0.02 * clean)

    def test_centroid_still_tracks_brightness(self):
        sr = 44100
        lo = [math.sin(2 * math.pi * 200 * i / sr) for i in range(sr // 4)]
        hi = [math.sin(2 * math.pi * 6000 * i / sr) for i in range(sr // 4)]
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
        self.assertTrue((self.dir / "blip.report.png").exists())
        self.assertIn("silence:", out)
        self.assertIn("loudness:", out)
        if HAVE_FFMPEG:
            self.assertEqual(rc, 0)
            self.assertTrue(ogg.exists())
        else:
            # No .ogg means no shippable master — that has to be a failure, or
            # nothing downstream can tell the render didn't produce anything.
            self.assertEqual(rc, 1)
            self.assertIn("NOT WRITTEN", err)
            self.assertTrue((self.dir / "blip.wav").exists())

    def test_missing_subtitle_warns(self):
        # The exit code tracks whether the .ogg was written, which is a separate
        # question from whether the cue drew a warning — so assert the warning.
        spec_path = self.dir / "s.sfx"
        spec_path.write_text(json.dumps({"layers": [{"freq": 440, "duration": 0.05}]}))
        rc, _, err = self._run([str(spec_path), "-o", str(self.dir / "s.ogg"), "--no-report"])
        self.assertEqual(rc, 0 if HAVE_FFMPEG else 1)
        self.assertIn("MISSING", err)

    def test_long_cue_warns(self):
        spec_path = self.dir / "l.sfx"
        spec_path.write_text(json.dumps({
            "subtitle": "t.s.l",
            "layers": [{"freq": 100, "duration": 3.0}],
        }))
        rc, _, err = self._run([str(spec_path), "-o", str(self.dir / "l.ogg"), "--no-report"])
        self.assertEqual(rc, 0 if HAVE_FFMPEG else 1)
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
            if HAVE_FFMPEG:
                self.assertEqual(rc, 0, f"{spec.name}: {err}")
            self.assertNotIn("warning", err, f"{spec.name} trips a quality warning: {err}")


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg is required to encode and decode a cue")
class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)
        self.blip = self.dir / "blip.sfx"
        self.blip.write_text(json.dumps({
            "subtitle": "t.s.b", "seed": 1,
            "layers": [{"freq": 880, "duration": 0.12}],
        }))
        self.other = self.dir / "other.sfx"
        self.other.write_text(json.dumps({
            "subtitle": "t.s.o", "seed": 1,
            "layers": [{"waveform": "saw", "freq": 220, "duration": 0.9}],
        }))

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = sfx.main(argv)
        return rc, out.getvalue(), err.getvalue()

    def test_freshly_rendered_cue_verifies(self):
        ogg = self.dir / "b.ogg"
        self._run([str(self.blip), "-o", str(ogg), "--no-report"])
        rc, out, err = self._run([str(self.blip), "-o", str(ogg), "--verify"])
        self.assertEqual(rc, 0, err)
        self.assertIn("matches", out)

    def test_trailing_encoder_padding_is_not_drift(self):
        # libvorbis finalizes some cue lengths with ~1000 samples of near-silent
        # padding past the final granule, and ffmpeg's Vorbis decode emits it.
        # A shipped cue whose only difference is trailing sub--60 dBFS silence
        # is still the spec's cue; raw stream length must not fail it.
        spec = sfx.parse_spec(self.blip.read_text())
        samples, sr = sfx.synthesize(spec)
        samples, _, _, _ = sfx.normalize_loudness(
            samples, sr, spec["loudness_lufs"], spec["peak_dbfs"])
        stats = sfx.compute_stats(samples, sr)
        padded = samples + [0.00005] * int(0.025 * sr)  # ~25 ms below -60 dBFS
        wav = self.dir / "padded.wav"
        sfx.write_wav(wav, padded, sr)
        ogg = self.dir / "padded.ogg"
        ok, why = sfx.encode_ogg(wav, ogg)
        self.assertTrue(ok, why)
        problems = sfx.verify_render(ogg, samples, sr, stats)
        self.assertEqual([p for p in problems if "duration" in p], [])

    def test_different_cue_under_that_name_is_drift(self):
        ogg = self.dir / "b.ogg"
        self._run([str(self.other), "-o", str(ogg), "--no-report"])
        rc, _, err = self._run([str(self.blip), "-o", str(ogg), "--verify"])
        self.assertEqual(rc, 1)
        self.assertIn("duration", err)

    def test_missing_cue_is_drift(self):
        rc, _, err = self._run([str(self.blip), "-o", str(self.dir / "gone.ogg"), "--verify"])
        self.assertEqual(rc, 1)
        self.assertIn("missing", err)

    def test_verify_without_a_target_fails_rather_than_guessing(self):
        # Falling back to the gitignored render beside the spec would let a
        # stale local file pass as a verified shipped cue.
        rc, _, err = self._run([str(self.blip), "--verify"])
        self.assertEqual(rc, 1)
        self.assertIn("no 'ships' target", err)

    def test_ships_field_locates_the_cue(self):
        shipped = self.dir / "assets" / "blip.ogg"
        spec = self.dir / "shipped.sfx"
        spec.write_text(json.dumps({
            "subtitle": "t.s.b", "seed": 1, "ships": str(shipped),
            "layers": [{"freq": 880, "duration": 0.12}],
        }))
        self._run([str(spec), "-o", str(shipped), "--no-report"])
        rc, out, err = self._run([str(spec), "--verify"])
        self.assertEqual(rc, 0, err)
        self.assertIn(str(shipped), out)

    def test_verify_writes_nothing(self):
        ogg = self.dir / "b.ogg"
        self._run([str(self.blip), "-o", str(ogg), "--verify"])
        self.assertFalse(ogg.exists())
        self.assertFalse((self.dir / "b.report.png").exists())

    def test_verify_all_walks_a_tree(self):
        # The member-facing entry point: sfx.py is vendored into every member
        # repo, so the repo-wide walk has to live in it.
        art = self.dir / "art" / "audio"
        art.mkdir(parents=True)
        shipped = self.dir / "assets" / "blip.ogg"
        linked = art / "blip.sfx"
        linked.write_text(json.dumps({
            "subtitle": "t.s.b", "seed": 1, "ships": str(shipped),
            "layers": [{"freq": 880, "duration": 0.12}],
        }))
        (art / "loose.sfx").write_text(json.dumps({
            "subtitle": "t.s.l", "layers": [{"freq": 440, "duration": 0.1}]}))

        rc, out, _ = self._run(["--verify-all", str(art)])
        self.assertEqual(rc, 1)                      # linked cue not shipped yet
        self.assertIn("1 verified, 1 drifted, 0 malformed, 0 blocked, 1 unlinked", out)

        self._run([str(linked), "-o", str(shipped), "--no-report"])
        rc, out, _ = self._run(["--verify-all", str(art), "-v"])
        self.assertEqual(rc, 0)
        self.assertIn("1 verified, 0 drifted, 0 malformed, 0 blocked, 1 unlinked", out)

    def test_verify_all_walks_subdirectories(self):
        # A repo that sorts its cues into folders is the one that most needs
        # the check; a top-level-only walk would green-light what it skipped.
        art = self.dir / "art" / "audio"
        (art / "ui").mkdir(parents=True)
        shipped = self.dir / "assets" / "deep.ogg"
        nested = art / "ui" / "deep.sfx"
        nested.write_text(json.dumps({
            "subtitle": "t.s.d", "seed": 1, "ships": str(shipped),
            "layers": [{"freq": 660, "duration": 0.1}],
        }))
        self._run([str(nested), "-o", str(shipped), "--no-report"])
        rc, out, _ = self._run(["--verify-all", str(art), "-v"])
        self.assertEqual(rc, 0)
        self.assertIn("1 verified", out)
        self.assertIn("deep.sfx", out)

    def test_a_malformed_cue_is_not_reported_as_drift(self):
        art = self.dir / "art" / "audio"
        art.mkdir(parents=True)
        (art / "bad.sfx").write_text(
            json.dumps({"ships": str(self.dir / "assets" / "bad.ogg"),
                        "layers": []}))     # a cue with nothing in it
        rc, out, _ = self._run(["--verify-all", str(art)])
        self.assertEqual(rc, 1)
        self.assertIn("BROKEN", out)
        self.assertNotIn("DRIFT", out)
        self.assertIn("0 verified, 0 drifted, 1 malformed, 0 blocked, 0 unlinked", out)

    def test_verify_all_on_a_missing_directory_is_not_a_failure(self):
        rc, out, _ = self._run(["--verify-all", str(self.dir / "nope")])
        self.assertEqual(rc, 0)
        self.assertIn("no such directory", out)

    def test_tolerances_clear_real_encode_drift(self):
        # Vorbis moves peak and centroid on every encode; the tolerances have to
        # absorb that or --verify cries drift on a file it just wrote.
        ogg = self.dir / "b.ogg"
        self._run([str(self.blip), "-o", str(ogg), "--no-report"])
        spec = sfx.parse_spec(self.blip.read_text())
        buf, sr = sfx.synthesize(spec)
        buf, _, _, _ = sfx.normalize_loudness(
            buf, sr, spec["loudness_lufs"], spec["peak_dbfs"])
        want = sfx.compute_stats(buf, sr)
        got = sfx.compute_stats(sfx.decode_audio(ogg, sr), sr)
        for key, tol in sfx.VERIFY_TOLERANCE.items():
            limit = tol * abs(want[key]) if key == "centroid_hz" else tol
            self.assertLess(abs(got[key] - want[key]), limit / 2.0,
                            f"{key} drifts more than half its tolerance on a "
                            f"clean re-encode — the tolerance is too tight")


if __name__ == "__main__":
    unittest.main()
