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


class _ErrResponse:
    """A CurseForge upload-API error response: a status code plus a JSON body."""

    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text or (json.dumps(payload) if payload is not None else "")

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def _slug_error(slug):
    return _ErrResponse(400, {
        "errorCode": publish.CF_INVALID_PROJECT_SLUG,
        "errorMessage": f"Invalid slug in project relations: '{slug}'",
    })


class DropInvalidSlugTest(unittest.TestCase):
    """CurseForge names the offending slug in a 1018; only that one may go.

    The regression this guards is silent and cost real listings: the previous
    code discarded *every* relation on any failure, so one stale sibling slug
    stripped the whole optional-dependency list off the published file.
    """

    def setUp(self):
        self.relations = [{"slug": s, "type": "optionalDependency"}
                          for s in ("emi", "jade", "ftbteams", "wthit")]

    def test_drops_only_the_named_slug(self):
        dropped = publish.drop_invalid_slug(self.relations, _slug_error("ftbteams"))
        self.assertEqual(dropped, "ftbteams")
        self.assertEqual([r["slug"] for r in self.relations],
                         ["emi", "jade", "wthit"])

    def test_unrelated_error_code_drops_nothing(self):
        resp = _ErrResponse(400, {"errorCode": 1009, "errorMessage": "bad version"})
        self.assertIsNone(publish.drop_invalid_slug(self.relations, resp))
        self.assertEqual(len(self.relations), 4)

    def test_a_500_drops_nothing(self):
        # 2026-08-29: CurseForge served 500s both with and without relations, so
        # a 5xx is never evidence that the relations are at fault.
        resp = _ErrResponse(500, {"errorCode": 500,
                                  "errorMessage": "An unhandled exception occurred"})
        self.assertIsNone(publish.drop_invalid_slug(self.relations, resp))
        self.assertEqual(len(self.relations), 4)

    def test_non_json_body_drops_nothing(self):
        self.assertIsNone(publish.drop_invalid_slug(self.relations,
                                                    _ErrResponse(502, None, "<html>")))
        self.assertEqual(len(self.relations), 4)

    def test_none_response_drops_nothing(self):
        self.assertIsNone(publish.drop_invalid_slug(self.relations, None))
        self.assertEqual(len(self.relations), 4)

    def test_slug_we_are_not_sending_returns_none(self):
        # Guards the peel loop against spinning forever on an unremovable name.
        self.assertIsNone(publish.drop_invalid_slug(self.relations,
                                                    _slug_error("not-in-list")))
        self.assertEqual(len(self.relations), 4)

    def test_unparseable_message_returns_none(self):
        resp = _ErrResponse(400, {"errorCode": publish.CF_INVALID_PROJECT_SLUG,
                                  "errorMessage": "something else entirely"})
        self.assertIsNone(publish.drop_invalid_slug(self.relations, resp))
        self.assertEqual(len(self.relations), 4)


class RequestWithRetriesTest(unittest.TestCase):
    """5xx and transport errors retry with growing delay; 4xx returns at once."""

    def _run(self, responses):
        calls = []
        delays = []

        def fake_request(method, url, **_kw):
            item = responses[len(calls)]
            calls.append(item)
            if isinstance(item, Exception):
                raise item
            return item

        with mock.patch.object(publish.requests, "request", fake_request), \
             mock.patch.object(publish.time, "sleep", delays.append):
            resp = publish.request_with_retries("POST", "https://example/api")
        return resp, calls, delays

    def test_4xx_returns_immediately_without_retrying(self):
        resp, calls, delays = self._run([_ErrResponse(400, {"errorCode": 1018})])
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(len(calls), 1)
        self.assertEqual(delays, [])

    def test_success_returns_immediately(self):
        resp, calls, delays = self._run([_ErrResponse(200, {"id": 1})])
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(calls), 1)
        self.assertEqual(delays, [])

    def test_5xx_retries_then_succeeds(self):
        responses = [_ErrResponse(500, {"errorCode": 500}),
                     _ErrResponse(500, {"errorCode": 500}),
                     _ErrResponse(201, {"id": 7})]
        resp, calls, delays = self._run(responses)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(len(calls), 3)
        self.assertEqual(delays, [10, 20])

    def test_backoff_grows_and_is_capped(self):
        responses = [_ErrResponse(500, {"errorCode": 500})] * publish.RETRY_ATTEMPTS
        resp, calls, delays = self._run(responses)
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(len(calls), publish.RETRY_ATTEMPTS)
        # One sleep fewer than attempts, doubling, capped at RETRY_MAX_DELAY.
        self.assertEqual(len(delays), publish.RETRY_ATTEMPTS - 1)
        self.assertEqual(delays, [10, 20, 40])
        self.assertLessEqual(max(delays), publish.RETRY_MAX_DELAY)

    def test_budget_survives_the_2026_08_29_curseforge_incident(self):
        # Four of five uploads 500'd that day and the release landed on the last
        # attempt the old 3-attempt budget allowed. The widened budget must
        # still have a spare attempt in that shape.
        responses = [_ErrResponse(500, {"errorCode": 500})] * 3 + [_ErrResponse(200, {"id": 9})]
        resp, calls, _ = self._run(responses)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(calls), 4)

    def test_transport_errors_retry_and_return_none(self):
        boom = publish.requests.RequestException("connection reset")
        resp, calls, delays = self._run([boom] * publish.RETRY_ATTEMPTS)
        self.assertIsNone(resp)
        self.assertEqual(len(calls), publish.RETRY_ATTEMPTS)
        self.assertEqual(delays, [10, 20, 40])


class CurseforgePublishRelationsTest(unittest.TestCase):
    """The peel loop end-to-end: bad slugs go one at a time, good ones survive.

    This is the behaviour the unit tests above only cover in pieces, and it is
    the one that decides what a player actually sees on the CurseForge listing.
    """

    ENV = {
        "CURSEFORGE_TOKEN": "tok",
        "CURSEFORGE_ID": "1234",
        "GAME_VERSIONS": "1.21.1",
        "LOADERS": "fabric",
        "ENVIRONMENT": "client_and_server",
        "TITLE": "Mymod v1.0.0",
        "PRERELEASE": "false",
    }

    def _publish(self, dep_slugs, responder):
        """Drive curseforge_publish with a scripted responder. Returns
        (ok, sent_relations_per_attempt)."""
        sent = []

        def fake_request(method, url, **kwargs):
            meta = json.loads(kwargs["data"]["metadata"])
            slugs = [r["slug"] for r in meta.get("relations", {}).get("projects", [])]
            sent.append(slugs)
            return responder(len(sent) - 1, slugs)

        deps = [{"id": s, "curseforge": s, "modrinth": s, "type": "optional"}
                for s in dep_slugs]
        with mock.patch.dict(os.environ, self.ENV, clear=False), \
             mock.patch.object(publish, "curseforge_resolve_versions",
                               return_value=[1, 2, 3]), \
             mock.patch.object(publish, "read_jar", return_value=b"jar"), \
             mock.patch.object(publish.requests, "request", fake_request), \
             mock.patch.object(publish.time, "sleep", lambda _s: None):
            ok = publish.curseforge_publish("build/libs/mymod-1.0.0.jar", "notes", deps)
        return ok, sent

    def test_one_bad_slug_costs_only_that_slug(self):
        def responder(i, slugs):
            if "ftbteams" in slugs:
                return _slug_error("ftbteams")
            return _ErrResponse(200, {"id": 42})

        ok, sent = self._publish(["emi", "jade", "ftbteams", "wthit"], responder)
        self.assertTrue(ok)
        self.assertEqual(len(sent), 2)
        # The retry keeps every relation that CurseForge did not object to.
        self.assertEqual(sent[-1], ["emi", "jade", "wthit"])

    def test_several_bad_slugs_peel_one_at_a_time(self):
        bad = {"ftbteams", "openpartiesandclaims"}

        def responder(i, slugs):
            for slug in slugs:
                if slug in bad:
                    return _slug_error(slug)
            return _ErrResponse(200, {"id": 43})

        ok, sent = self._publish(
            ["emi", "ftbteams", "jade", "openpartiesandclaims", "wthit"], responder)
        self.assertTrue(ok)
        self.assertEqual(sent[-1], ["emi", "jade", "wthit"])

    def test_all_relations_bad_still_publishes(self):
        def responder(i, slugs):
            if slugs:
                return _slug_error(slugs[0])
            return _ErrResponse(200, {"id": 44})

        ok, sent = self._publish(["ftbteams", "openpartiesandclaims"], responder)
        self.assertTrue(ok)
        self.assertEqual(sent[-1], [])

    def test_good_relations_are_never_stripped_by_a_500(self):
        # The 2026-08-29 shape: transient 500s, relations blameless. The old
        # code fell back to no-relations here and published a bare listing.
        state = {"n": 0}

        def responder(i, slugs):
            state["n"] += 1
            # Three failures: one more than the old 3-attempt budget could
            # absorb, so the old code exhausted it and stripped the relations.
            if state["n"] <= 3:
                return _ErrResponse(500, {"errorCode": 500,
                                          "errorMessage": "An unhandled exception occurred"})
            return _ErrResponse(200, {"id": 45})

        ok, sent = self._publish(["emi", "jade", "wthit"], responder)
        self.assertTrue(ok)
        self.assertEqual(sent[-1], ["emi", "jade", "wthit"])

    def test_persistent_failure_falls_back_to_no_relations(self):
        # Unattributed persistent failure: publishing bare beats failing the
        # release, and the fallback must still fire.
        def responder(i, slugs):
            if slugs:
                return _ErrResponse(400, {"errorCode": 9999,
                                          "errorMessage": "something structural"})
            return _ErrResponse(200, {"id": 46})

        ok, sent = self._publish(["emi", "jade"], responder)
        self.assertTrue(ok)
        self.assertEqual(sent[-1], [])

    def test_hard_failure_returns_false(self):
        ok, _ = self._publish(["emi"], lambda i, slugs: _ErrResponse(
            403, {"errorCode": 403, "errorMessage": "forbidden"}))
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
