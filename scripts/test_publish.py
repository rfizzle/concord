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
from unittest import mock

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


class _FakeResponse:
    def __init__(self, payload, ok=True):
        self._payload = payload
        self.ok = ok

    def json(self):
        return self._payload


# A synthetic CurseForge catalogue: the environment group carries Client/Server,
# and a decoy "bukkit" group carries a same-named 1.21.1 the upload API rejects,
# so the type-group gating — not the bare name — is what must be exercised.
_VERSION_TYPES = [
    {"id": 1, "slug": "minecraft-1-21"},
    {"id": 2, "slug": "modloader"},
    {"id": 3, "slug": "environment"},
    {"id": 4, "slug": "bukkit-1-21"},
]
_VERSIONS = [
    {"id": 100, "gameVersionTypeID": 1, "name": "1.21.1"},
    {"id": 101, "gameVersionTypeID": 2, "name": "Fabric"},
    {"id": 102, "gameVersionTypeID": 3, "name": "Client"},
    {"id": 103, "gameVersionTypeID": 3, "name": "Server"},
    {"id": 104, "gameVersionTypeID": 4, "name": "1.21.1"},  # decoy, wrong group
]


def _fake_catalogue(versions=_VERSIONS, types=_VERSION_TYPES,
                    versions_ok=True, types_ok=True):
    def get(url, **_kwargs):
        if url.endswith("/game/versions"):
            return _FakeResponse(versions, ok=versions_ok)
        if url.endswith("/game/version-types"):
            return _FakeResponse(types, ok=types_ok)
        raise AssertionError(f"unexpected URL {url}")
    return get


def _resolve(environment, **catalogue_kwargs):
    with mock.patch.object(publish.requests, "get",
                           _fake_catalogue(**catalogue_kwargs)):
        return publish.curseforge_resolve_versions(
            "token", ["1.21.1"], ["fabric"], environment)


class CurseforgeEnvironmentNamesTest(unittest.TestCase):
    def test_client_and_server_maps_to_both(self):
        self.assertEqual(publish.curseforge_environment_names("client_and_server"),
                         {"client", "server"})

    def test_client_only_maps_to_client(self):
        self.assertEqual(publish.curseforge_environment_names("client_only"),
                         {"client"})

    def test_server_only_variants_map_to_server(self):
        self.assertEqual(publish.curseforge_environment_names("server_only"),
                         {"server"})
        self.assertEqual(publish.curseforge_environment_names("dedicated_server_only"),
                         {"server"})

    def test_client_only_server_optional_maps_to_both(self):
        self.assertEqual(
            publish.curseforge_environment_names("client_only_server_optional"),
            {"client", "server"})

    def test_empty_or_unknown_falls_back_to_both(self):
        self.assertEqual(publish.curseforge_environment_names(""),
                         {"client", "server"})
        self.assertEqual(publish.curseforge_environment_names("something-new"),
                         {"client", "server"})


class CurseforgeResolveVersionsTest(unittest.TestCase):
    def test_default_env_tags_minecraft_loader_and_both_environments(self):
        # The regression: without an environment id CurseForge rejects with 1021.
        self.assertEqual(_resolve("client_and_server"), [100, 101, 102, 103])

    def test_client_only_omits_the_server_id(self):
        ids = _resolve("client_only")
        self.assertIn(102, ids)      # Client
        self.assertNotIn(103, ids)   # Server

    def test_server_only_variants_omit_the_client_id(self):
        for value in ("server_only", "dedicated_server_only"):
            ids = _resolve(value)
            self.assertIn(103, ids, value)       # Server
            self.assertNotIn(102, ids, value)    # Client

    def test_client_only_server_optional_tags_both(self):
        ids = _resolve("client_only_server_optional")
        self.assertIn(102, ids)
        self.assertIn(103, ids)

    def test_decoy_same_named_version_in_wrong_group_is_ignored(self):
        # 1.21.1 also exists under a bukkit group (id 104); only the minecraft one counts.
        ids = _resolve("client_and_server")
        self.assertIn(100, ids)
        self.assertNotIn(104, ids)

    def test_missing_environment_group_blocks_the_upload(self):
        # A catalogue with no Client/Server entries must resolve to [] so the
        # upload is blocked rather than rejected with error 1021.
        no_env = [v for v in _VERSIONS if v["gameVersionTypeID"] != 3]
        self.assertEqual(_resolve("client_and_server", versions=no_env), [])

    def test_catalogue_fetch_failure_returns_none(self):
        self.assertIsNone(_resolve("client_and_server", versions_ok=False))
        self.assertIsNone(_resolve("client_and_server", types_ok=False))


if __name__ == "__main__":
    unittest.main()
