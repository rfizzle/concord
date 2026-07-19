#!/usr/bin/env python3
"""Unit tests for scripts/check-gametest-manifest.py.

Hermetic: each test builds a throwaway <root>/<id> member tree plus a members.json
in a temp dir, then drives main(). Run with:

    python3 -m unittest scripts.test_check_gametest_manifest
    python3 scripts/test_check_gametest_manifest.py
"""

from __future__ import annotations

import importlib.util
import io
import json
import pathlib
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

_HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "check_gametest_manifest", _HERE / "check-gametest-manifest.py"
)
checker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(checker)


SHIPPED_CLEAN = {
    "schemaVersion": 1,
    "id": "meridian",
    "version": "${version}",
    "entrypoints": {"main": ["com.rfizzle.meridian.Meridian"]},
}

COMPANION_CLEAN = {
    "schemaVersion": 1,
    "id": "meridian-gametest",
    "version": "1.0.0",
    "environment": "*",
    "entrypoints": {"fabric-gametest": ["com.rfizzle.meridian.gametest.SmokeGameTest"]},
    "depends": {"meridian": "*"},
}


class CheckGametestManifest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)
        self.members = self.root / "members.json"
        self.members.write_text(
            json.dumps({"members": [{"id": "meridian"}]}), encoding="utf-8"
        )
        self.member_dir = self.root / "meridian"
        self.member_dir.mkdir(parents=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self, relative: str, content) -> None:
        path = self.member_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        text = content if isinstance(content, str) else json.dumps(content)
        path.write_text(text, encoding="utf-8")

    def _shipped(self, manifest=None) -> None:
        self._write(
            "src/main/resources/fabric.mod.json",
            SHIPPED_CLEAN if manifest is None else manifest,
        )

    def _companion(self, manifest=None) -> None:
        self._write(
            "src/gametest/resources/fabric.mod.json",
            COMPANION_CLEAN if manifest is None else manifest,
        )

    def _gametest_source(self, relative: str = "SmokeGameTest.java") -> None:
        self._write(f"src/gametest/java/com/rfizzle/meridian/gametest/{relative}", "")

    def _run(self) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = checker.main(
                ["--root", str(self.root), "--members", str(self.members)]
            )
        return code, out.getvalue(), err.getvalue()

    # --- the registered-correctly baseline ---------------------------------

    def test_split_manifest_passes_with_no_notes(self) -> None:
        self._shipped()
        self._companion()
        self._gametest_source()
        code, out, err = self._run()
        self.assertEqual(code, 0, err)
        self.assertEqual(err, "")
        self.assertIn("register from their own manifest", out)

    def test_member_without_gametests_is_a_note_not_drift(self) -> None:
        self._shipped()
        code, out, err = self._run()
        self.assertEqual(code, 0, err)
        self.assertIn("no gametest sources", err)

    # --- drift --------------------------------------------------------------

    def test_entrypoints_in_shipped_manifest_are_drift(self) -> None:
        shipped = dict(SHIPPED_CLEAN)
        shipped["entrypoints"] = {
            "main": ["com.rfizzle.meridian.Meridian"],
            "fabric-gametest": ["com.rfizzle.meridian.gametest.SmokeGameTest"],
        }
        self._shipped(shipped)
        self._companion()
        self._gametest_source()
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("declares 1 fabric-gametest entrypoint(s)", err)

    def test_gametest_sources_without_companion_manifest_are_drift(self) -> None:
        self._shipped()
        self._gametest_source()
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("the suite never runs", err)

    def test_nested_gametest_sources_are_found(self) -> None:
        """Suites in subpackages count, or a member reads as having none."""
        self._shipped()
        self._gametest_source("util/MockPlayersGameTest.java")
        code, _, err = self._run()
        self.assertEqual(code, 1, err)
        self.assertIn("the suite never runs", err)

    def test_placeholder_version_in_companion_is_drift(self) -> None:
        companion = dict(COMPANION_CLEAN)
        companion["version"] = "${version}"
        self._shipped()
        self._companion(companion)
        self._gametest_source()
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("pin it literally", err)

    def test_unparseable_companion_manifest_is_drift_not_a_pass(self) -> None:
        """A syntax error must not read as 'declares no entrypoints'."""
        self._shipped()
        self._write("src/gametest/resources/fabric.mod.json", "{ not json")
        self._gametest_source()
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("unparseable", err)

    def test_unparseable_shipped_manifest_is_drift(self) -> None:
        self._write("src/main/resources/fabric.mod.json", "{ not json")
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("unparseable", err)

    # --- notes, which must not fail the run ---------------------------------

    def test_off_convention_companion_id_is_a_note(self) -> None:
        companion = dict(COMPANION_CLEAN)
        companion["id"] = "meridian-tests"
        self._shipped()
        self._companion(companion)
        self._gametest_source()
        code, _, err = self._run()
        self.assertEqual(code, 0, err)
        self.assertIn("expected 'meridian-gametest'", err)

    def test_companion_not_depending_on_main_mod_is_a_note(self) -> None:
        companion = dict(COMPANION_CLEAN)
        companion["depends"] = {"fabric-api": "*"}
        self._shipped()
        self._companion(companion)
        self._gametest_source()
        code, _, err = self._run()
        self.assertEqual(code, 0, err)
        self.assertIn("does not depend on 'meridian'", err)

    def test_companion_registering_nothing_is_a_note(self) -> None:
        companion = dict(COMPANION_CLEAN)
        companion["entrypoints"] = {}
        self._shipped()
        self._companion(companion)
        self._gametest_source()
        code, _, err = self._run()
        self.assertEqual(code, 0, err)
        self.assertIn("registers no fabric-gametest entrypoints", err)

    def test_missing_shipped_manifest_is_a_note(self) -> None:
        code, _, err = self._run()
        self.assertEqual(code, 0, err)
        self.assertIn("cannot check", err)

    # --- harness ------------------------------------------------------------

    def test_member_not_checked_out_is_skipped(self) -> None:
        self.members.write_text(
            json.dumps({"members": [{"id": "absent"}]}), encoding="utf-8"
        )
        code, out, err = self._run()
        self.assertEqual(code, 0, err)
        self.assertIn("skip: absent", err)
        self.assertIn("nothing to compare", out)

    def test_malformed_members_json_exits_two(self) -> None:
        self.members.write_text("{ not json", encoding="utf-8")
        with self.assertRaises(SystemExit) as raised:
            self._run()
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
