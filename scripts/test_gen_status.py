#!/usr/bin/env python3
"""Unit tests for scripts/gen-status.py.

Hermetic: a canned fetch callable stands in for the GitHub and Modrinth APIs,
so no network is touched. Run with:

    python3 -m unittest scripts.test_gen_status
    python3 scripts/test_gen_status.py
"""

from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import unittest
import urllib.parse

_HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("gen_status", _HERE / "gen-status.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


# The block vocabulary template/eleventy.config.cjs validates. The generator
# must never emit a type outside this set or the site build fails loudly.
TEMPLATE_BLOCK_TYPES = {
    "prose", "note", "sub", "table", "code", "cards",
    "list", "steps", "faq", "examples", "panel",
}

MERIDIAN = {
    "id": "meridian",
    "name": "Meridian",
    "url": "https://meridian.rfizzle.com",
    "store": {"modrinth": {"id": "qywREjYt", "slug": "meridian-enchanting-overhaul"}},
    "status": "released",
    "conformance": {"layoutMigrated": True},
}

RESPITE = {
    "id": "respite",
    "name": "Respite",
    "url": "https://respite.rfizzle.com",
    "store": {"modrinth": {"slug": "respite-vitality-overhaul"}},
    "status": "in-development",
    "conformance": {"layoutMigrated": False},
}


def _release_url(mid: str) -> str:
    return f"{gen.GITHUB_API}/repos/rfizzle/{mid}/releases/latest"


def _ci_url(mid: str) -> str:
    return (
        f"{gen.GITHUB_API}/repos/rfizzle/{mid}/actions/workflows/ci.yml/runs"
        "?branch=master&per_page=1&exclude_pull_requests=true"
    )


def _search_url(mid: str) -> str:
    query = urllib.parse.urlencode(
        {"q": f"repo:rfizzle/{mid} type:issue state:open", "per_page": 1}
    )
    return f"{gen.GITHUB_API}/search/issues?{query}"


def _modrinth_url(lookup: str) -> str:
    return f"{gen.MODRINTH_API}/project/{lookup}"


def make_fetch(responses: dict):
    """A fetch stand-in: exact-URL lookup, 404 for anything unlisted."""
    def fetch(url, headers=None):
        return responses.get(url, (404, None))
    return fetch


MERIDIAN_LIVE = {
    _release_url("meridian"): (200, {"tag_name": "v1.0.0", "published_at": "2026-07-01T12:43:41Z"}),
    _ci_url("meridian"): (200, {"workflow_runs": [
        {"status": "completed", "conclusion": "success", "updated_at": "2026-07-10T07:45:35Z"}
    ]}),
    _search_url("meridian"): (200, {"total_count": 8}),
    _modrinth_url("qywREjYt"): (200, {
        "slug": "meridian-enchanting-overhaul", "downloads": 1234, "followers": 5,
    }),
}


def _walk_blocks(blocks):
    for b in blocks:
        yield b
        if b.get("type") == "sub":
            yield from _walk_blocks(b.get("blocks", []))


class FetchMemberTests(unittest.TestCase):
    def test_happy_path(self):
        m = gen.fetch_member(MERIDIAN, make_fetch(MERIDIAN_LIVE))
        self.assertEqual(m["release"], {"tag": "v1.0.0", "date": "2026-07-01"})
        self.assertEqual(m["ci"]["conclusion"], "success")
        self.assertEqual(m["ci"]["date"], "2026-07-10")
        self.assertEqual(m["openIssues"], 8)
        self.assertEqual(m["modrinth"]["downloads"], 1234)
        self.assertEqual(m["repo"], "rfizzle/meridian")
        self.assertTrue(m["layoutMigrated"])

    def test_everything_missing_is_null_not_error(self):
        # All endpoints 404 (unreleased repo, draft Modrinth listing).
        m = gen.fetch_member(RESPITE, make_fetch({}))
        self.assertIsNone(m["release"])
        self.assertIsNone(m["ci"])
        self.assertIsNone(m["openIssues"])
        self.assertIsNone(m["modrinth"])
        self.assertEqual(m["status"], "in-development")

    def test_network_failure_is_null(self):
        dead = lambda url, headers=None: (0, None)
        m = gen.fetch_member(MERIDIAN, dead)
        self.assertIsNone(m["release"])
        self.assertIsNone(m["ci"])
        self.assertIsNone(m["openIssues"])
        self.assertIsNone(m["modrinth"])


class BuildStatusTests(unittest.TestCase):
    def test_totals(self):
        doc = {"members": [MERIDIAN, RESPITE]}
        data = gen.build_status(doc, make_fetch(MERIDIAN_LIVE))
        self.assertEqual(data["totals"]["members"], 2)
        self.assertEqual(data["totals"]["released"], 1)
        self.assertEqual(data["totals"]["downloads"], 1234)
        self.assertEqual(data["totals"]["followers"], 5)
        self.assertEqual(data["totals"]["openIssues"], 8)

    def test_totals_null_when_nothing_reachable(self):
        data = gen.build_status({"members": [RESPITE]}, make_fetch({}))
        self.assertIsNone(data["totals"]["downloads"])
        self.assertIsNone(data["totals"]["openIssues"])
        self.assertEqual(data["totals"]["members"], 1)

    def test_members_json_order_preserved(self):
        data = gen.build_status({"members": [RESPITE, MERIDIAN]}, make_fetch(MERIDIAN_LIVE))
        self.assertEqual([m["id"] for m in data["members"]], ["respite", "meridian"])


class GeneratedStampTests(unittest.TestCase):
    def _data(self):
        return gen.build_status({"members": [MERIDIAN]}, make_fetch(MERIDIAN_LIVE))

    def test_stamp_kept_when_data_unchanged(self):
        previous = {"generated": "2026-07-01", **self._data()}
        # Round-trip through JSON like the committed file would be.
        previous = json.loads(json.dumps(previous))
        stamp = gen.resolve_generated(self._data(), previous, "2026-07-11")
        self.assertEqual(stamp, "2026-07-01")

    def test_stamp_bumped_when_data_changed(self):
        previous = {"generated": "2026-07-01", **self._data()}
        changed = self._data()
        changed["totals"]["downloads"] = 9999
        stamp = gen.resolve_generated(changed, previous, "2026-07-11")
        self.assertEqual(stamp, "2026-07-11")

    def test_no_previous_file(self):
        self.assertEqual(gen.resolve_generated(self._data(), None, "2026-07-11"), "2026-07-11")


class RenderTests(unittest.TestCase):
    def _status(self):
        data = gen.build_status({"members": [MERIDIAN, RESPITE]}, make_fetch(MERIDIAN_LIVE))
        return {"generated": "2026-07-11", **data}

    def test_page_uses_only_template_block_types(self):
        page = gen.render_status_page(self._status())
        for section in page["sections"]:
            for b in _walk_blocks(section["blocks"]):
                self.assertIn(b["type"], TEMPLATE_BLOCK_TYPES)

    def test_table_rows_match_headers(self):
        page = gen.render_status_page(self._status())
        table = page["sections"][1]["blocks"][0]
        self.assertEqual(table["type"], "table")
        for row in table["rows"]:
            self.assertEqual(len(row), len(table["headers"]))

    def test_released_member_row(self):
        row = gen.member_row(gen.fetch_member(MERIDIAN, make_fetch(MERIDIAN_LIVE)))
        self.assertIn("meridian.rfizzle.com", row[0])
        self.assertIn("released", row[1])
        self.assertEqual(row[2], "v1.0.0")
        self.assertEqual(row[3], "2026-07-01")
        self.assertIn("badge.svg", row[4])
        self.assertIn("1,234", row[5])
        self.assertIn("modrinth.com/mod/meridian-enchanting-overhaul", row[5])
        self.assertIn("/issues'>8</a>", row[6])
        self.assertEqual(row[7], "migrated")

    def test_degraded_member_row_renders_dashes(self):
        row = gen.member_row(gen.fetch_member(RESPITE, make_fetch({})))
        self.assertIn("in development", row[1])
        self.assertEqual(row[2:7], [gen.DASH] * 5)
        self.assertEqual(row[7], "pending")

    def test_page_note_carries_generated_date(self):
        page = gen.render_status_page(self._status())
        table = page["sections"][1]["blocks"][0]
        self.assertIn("2026-07-11", table["note"])

    def test_render_is_deterministic(self):
        a = json.dumps(gen.render_status_page(self._status()), sort_keys=True)
        b = json.dumps(gen.render_status_page(self._status()), sort_keys=True)
        self.assertEqual(a, b)

    def test_page_is_json_serializable(self):
        json.dumps(gen.render_status_page(self._status()))


class PatchIndexTests(unittest.TestCase):
    def _index(self):
        return {
            "type": "home",
            "sections": [
                {"title": "Hand-authored", "blocks": [{"type": "prose", "html": ["x"]}]},
                {"id": gen.INDEX_STATUS_SECTION_ID, "title": "Suite status", "blocks": []},
            ],
        }

    def _status(self):
        data = gen.build_status({"members": [MERIDIAN]}, make_fetch(MERIDIAN_LIVE))
        return {"generated": "2026-07-11", **data}

    def test_patch_replaces_only_marked_section(self):
        doc = self._index()
        untouched = copy.deepcopy(doc["sections"][0])
        self.assertTrue(gen.patch_index(doc, self._status()))
        self.assertEqual(doc["sections"][0], untouched)
        blocks = doc["sections"][1]["blocks"]
        self.assertEqual(blocks[0]["type"], "cards")
        self.assertEqual(blocks[1]["type"], "note")
        for b in blocks:
            self.assertIn(b["type"], TEMPLATE_BLOCK_TYPES)

    def test_patch_is_idempotent(self):
        doc = self._index()
        self.assertTrue(gen.patch_index(doc, self._status()))
        self.assertFalse(gen.patch_index(doc, self._status()))

    def test_missing_section_is_a_noop(self):
        doc = {"sections": [{"title": "Hand-authored", "blocks": []}]}
        before = copy.deepcopy(doc)
        self.assertFalse(gen.patch_index(doc, self._status()))
        self.assertEqual(doc, before)


if __name__ == "__main__":
    unittest.main()
