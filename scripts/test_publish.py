#!/usr/bin/env python3
"""Unit tests for scripts/release/publish.py.

Hermetic: each test builds a throwaway member source tree in a temp dir, chdirs
into it, and drives the resolver the way the release workflow does — from the
member repo root, with no FABRIC_MOD_JSON set. Run with:

    python3 -m unittest scripts.test_publish
    python3 scripts/test_publish.py
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest

_HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "publish", _HERE / "release" / "publish.py"
)
publish = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(publish)


SHIPPED = {
    "schemaVersion": 1,
    "id": "mymod",
    "version": "${version}",
    "suggests": {"sodium": "*", "modmenu": "*"},
    "recommends": {"fabric-api": "*"},
}

GAMETEST = {
    "schemaVersion": 1,
    "id": "mymod-gametest",
    "version": "1.0.0",
    "depends": {"mymod": "*"},
}


@contextlib.contextmanager
def member_tree(*, shipped=True, gametest=False):
    """A member repo root containing the requested manifests, as cwd."""
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        if shipped:
            path = root / "src" / "main" / "resources" / "fabric.mod.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(SHIPPED), encoding="utf-8")
        if gametest:
            path = root / "src" / "gametest" / "resources" / "fabric.mod.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(GAMETEST), encoding="utf-8")
        prev = os.getcwd()
        os.chdir(root)
        try:
            yield root
        finally:
            os.chdir(prev)


class FindFabricModJsonTest(unittest.TestCase):
    def setUp(self):
        # The resolver consults FABRIC_MOD_JSON first; a stray value in the
        # ambient environment would mask what these tests are asserting.
        self._saved = os.environ.pop("FABRIC_MOD_JSON", None)

    def tearDown(self):
        if self._saved is not None:
            os.environ["FABRIC_MOD_JSON"] = self._saved

    def test_resolves_shipped_manifest_when_it_is_the_only_one(self):
        with member_tree():
            found = publish.find_fabric_mod_json()
            self.assertIsNotNone(found)
            self.assertEqual(
                json.loads(pathlib.Path(found).read_text(encoding="utf-8"))["id"],
                "mymod",
            )

    def test_skips_the_gametest_manifest_that_sorts_first(self):
        """src/gametest sorts ahead of src/main; picking it drops every optional dep."""
        with member_tree(gametest=True):
            found = publish.find_fabric_mod_json()
            self.assertIsNotNone(found)
            self.assertEqual(
                json.loads(pathlib.Path(found).read_text(encoding="utf-8"))["id"],
                "mymod",
                "resolved the gametest manifest instead of the shipped one",
            )

    def test_optional_deps_survive_a_split_manifest_layout(self):
        """The regression that matters: the listing keeps its suggests/recommends."""
        with member_tree(gametest=True):
            deps = publish.load_dependencies()
            self.assertEqual(
                sorted(d["id"] for d in deps),
                ["fabric-api", "modmenu", "sodium"],
            )

    def test_explicit_override_still_wins(self):
        with member_tree(gametest=True) as root:
            override = str(root / "src" / "gametest" / "resources" / "fabric.mod.json")
            os.environ["FABRIC_MOD_JSON"] = override
            try:
                self.assertEqual(publish.find_fabric_mod_json(), override)
            finally:
                del os.environ["FABRIC_MOD_JSON"]

    def test_gametest_manifest_alone_resolves_to_nothing(self):
        """Better no dependencies than dependencies read off the wrong mod."""
        with member_tree(shipped=False, gametest=True):
            self.assertIsNone(publish.find_fabric_mod_json())

    def test_no_manifest_at_all_resolves_to_nothing(self):
        with member_tree(shipped=False):
            self.assertIsNone(publish.find_fabric_mod_json())


if __name__ == "__main__":
    unittest.main()
