#!/usr/bin/env python3
"""Unit tests for scripts/check-toolchain-drift.py.

Hermetic: each test builds a throwaway <root>/<id> member tree plus a canonical
versions-common.properties and members.json in a temp dir, then drives main().
Run with:

    python3 -m unittest scripts.test_check_toolchain_drift
    python3 scripts/test_check_toolchain_drift.py
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
    "check_toolchain_drift", _HERE / "check-toolchain-drift.py"
)
checker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(checker)


CANONICAL = """\
# Suite toolchain.
minecraft_version=1.21.1
loader_version=0.16.10
fabric_version=0.116.1+1.21.1
loom_version=1.9-SNAPSHOT
java_version=21
"""

# A gradle.properties carrying the canonical toolchain pins plus the per-repo
# values a member is free to vary.
GRADLE_MATCH = """\
minecraft_version=1.21.1
loader_version=0.16.10
fabric_version=0.116.1+1.21.1
mod_version=0.0.0
loom_version=1.9-SNAPSHOT
emi_version=1.1.22+1.21.1
java_version=21
org.gradle.jvmargs=-Xmx3g
"""


class CheckToolchainDrift(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)
        self.canonical = self.root / "versions-common.properties"
        self.canonical.write_text(CANONICAL, encoding="utf-8")
        self.members = self.root / "members.json"
        self.members.write_text(
            json.dumps({"members": [{"id": "meridian"}]}), encoding="utf-8"
        )
        self.member_dir = self.root / "meridian"
        self.member_dir.mkdir(parents=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self, name: str, content: str) -> None:
        (self.member_dir / name).write_text(content, encoding="utf-8")

    def _run(self) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = checker.main(
                [
                    "--root",
                    str(self.root),
                    "--canonical",
                    str(self.canonical),
                    "--members",
                    str(self.members),
                ]
            )
        return code, out.getvalue(), err.getvalue()

    def test_gradle_properties_match_passes(self) -> None:
        self._write("gradle.properties", GRADLE_MATCH)
        code, out, err = self._run()
        self.assertEqual(code, 0, err)
        self.assertIn("all member toolchains match", out)

    def test_behind_in_gradle_properties_is_drift(self) -> None:
        self._write(
            "gradle.properties",
            GRADLE_MATCH.replace("minecraft_version=1.21.1", "minecraft_version=1.21.0"),
        )
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("minecraft_version", err)
        self.assertIn("gradle.properties pins '1.21.0'", err)
        self.assertIn("expected '1.21.1'", err)

    def test_unpinned_key_is_note_not_drift(self) -> None:
        # Drop loom_version from gradle.properties entirely — an adoption gap
        # (the pin isn't sourced from the suite file), not a version lag.
        gp = "\n".join(
            l for l in GRADLE_MATCH.splitlines() if not l.startswith("loom_version")
        )
        self._write("gradle.properties", gp + "\n")
        code, _, err = self._run()
        self.assertEqual(code, 0, err)
        self.assertIn("loom_version: not pinned", err)
        self.assertIn("adopt the suite pin", err)

    def test_no_properties_files_is_note_not_drift(self) -> None:
        code, _, err = self._run()
        self.assertEqual(code, 0, err)
        self.assertIn("cannot compare", err)

    def test_adopted_member_reads_versions_common(self) -> None:
        # Adopted: toolchain keys live in the synced file, gradle.properties has
        # only per-repo values.
        self._write("versions-common.properties", CANONICAL)
        self._write(
            "gradle.properties",
            "mod_version=0.0.0\nemi_version=1.1.22+1.21.1\norg.gradle.jvmargs=-Xmx3g\n",
        )
        code, out, err = self._run()
        self.assertEqual(code, 0, err)
        self.assertIn("all member toolchains match", out)

    def test_synced_file_wins_over_gradle_and_notes_stale_duplicate(self) -> None:
        # Synced file matches canonical, but a stale gradle.properties pin still
        # shadows it — a note, not drift.
        self._write("versions-common.properties", CANONICAL)
        self._write(
            "gradle.properties",
            GRADLE_MATCH.replace("minecraft_version=1.21.1", "minecraft_version=1.20.6"),
        )
        code, _, err = self._run()
        self.assertEqual(code, 0, err)
        self.assertIn("stale duplicate", err)
        self.assertIn("1.20.6", err)

    def test_behind_synced_file_is_drift(self) -> None:
        # Member merged an older sync: versions-common.properties is behind.
        self._write(
            "versions-common.properties",
            CANONICAL.replace("fabric_version=0.116.1+1.21.1", "fabric_version=0.100.0+1.21.1"),
        )
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("versions-common.properties pins '0.100.0+1.21.1'", err)

    def test_missing_canonical_exits_2(self) -> None:
        self.canonical.unlink()
        with self.assertRaises(SystemExit) as cm:
            self._run()
        self.assertEqual(cm.exception.code, 2)

    def test_empty_canonical_exits_2(self) -> None:
        self.canonical.write_text("# only comments\n", encoding="utf-8")
        with self.assertRaises(SystemExit) as cm:
            self._run()
        self.assertEqual(cm.exception.code, 2)

    def test_no_members_checked_out_passes(self) -> None:
        self.members.write_text(
            json.dumps({"members": [{"id": "absent"}]}), encoding="utf-8"
        )
        code, out, err = self._run()
        self.assertEqual(code, 0)
        self.assertIn("not checked out", err)

    def test_whitespace_and_comments_parsed(self) -> None:
        self._write(
            "gradle.properties",
            "  minecraft_version = 1.21.1 \n# comment\n! bang comment\n"
            "loader_version=0.16.10\nfabric_version=0.116.1+1.21.1\n"
            "loom_version=1.9-SNAPSHOT\njava_version=21\n",
        )
        code, out, err = self._run()
        self.assertEqual(code, 0, err)


class RealCanonical(unittest.TestCase):
    def test_repo_canonical_parses_and_has_toolchain_keys(self) -> None:
        repo_root = _HERE.parent
        pins = checker.load_canonical(repo_root / "propagate" / "versions-common.properties")
        self.assertEqual(
            set(pins),
            {
                "minecraft_version",
                "loader_version",
                "fabric_version",
                "loom_version",
                "java_version",
            },
        )
        for value in pins.values():
            self.assertTrue(value)


if __name__ == "__main__":
    unittest.main()
