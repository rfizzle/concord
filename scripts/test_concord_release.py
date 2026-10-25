#!/usr/bin/env python3
"""Unit tests for propagate/scripts/concord-release.py (git and gh are faked).

    python3 -m unittest scripts.test_concord_release
"""

from __future__ import annotations

import importlib.util
import io
import json
import pathlib
import unittest
from contextlib import redirect_stderr, redirect_stdout

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "concord_release", _ROOT / "propagate" / "scripts" / "concord-release.py"
)
cr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cr)

SHA = "a" * 40
GREEN = [{"id": 1, "name": "ci / test", "status": "completed", "conclusion": "success"}]


def check(status, conclusion, id=1, name="ci / test"):
    return {"id": id, "name": name, "status": status, "conclusion": conclusion}


class FakeRunner:
    def __init__(self, **kw):
        self.s = dict(
            status="", branch="master", head=SHA, remote=SHA,
            local_tags=[], remote_tags=[], origin="git@github.com:rfizzle/mod.git",
            ancestor=True, checks=GREEN,
        )
        self.s.update(kw)
        self.calls: list[list[str]] = []

    def __call__(self, cmd):
        self.calls.append(cmd)
        s = self.s
        if cmd[:2] == ["git", "status"]:
            return 0, s["status"]
        if cmd[:3] == ["git", "rev-parse", "--abbrev-ref"]:
            return 0, s["branch"]
        if cmd[:2] == ["git", "fetch"]:
            return 0, ""
        if cmd[:3] == ["git", "rev-parse", "HEAD"]:
            return 0, s["head"]
        if cmd[:3] == ["git", "rev-parse", "origin/master"]:
            return 0, s["remote"]
        if cmd[:4] == ["git", "rev-parse", "-q", "--verify"]:
            tag = cmd[4].removeprefix("refs/tags/")
            return (0, SHA) if tag in s["local_tags"] else (1, "")
        if cmd[:2] == ["git", "rev-parse"] and cmd[2].endswith("^{commit}"):
            return 0, SHA
        if cmd[:3] == ["git", "tag", "-l"]:
            return 0, "\n".join(s["local_tags"])
        if cmd[:3] == ["git", "ls-remote", "--tags"]:
            pat = cmd[4]
            tags = [t for t in s["remote_tags"] if pat == "refs/tags/v*" or pat == f"refs/tags/{t}"]
            return 0, "".join(f"{SHA}\trefs/tags/{t}\n" for t in tags)
        if cmd[:3] == ["git", "remote", "get-url"]:
            return 0, s["origin"]
        if cmd[:3] == ["git", "merge-base", "--is-ancestor"]:
            return (0, "") if s["ancestor"] else (1, "")
        if cmd[0] == "gh":
            return 0, "\n".join(json.dumps(c) for c in s["checks"])
        if cmd[:2] in (["git", "tag"], ["git", "push"]):
            return 0, ""
        raise AssertionError(f"unexpected command {cmd}")

    def ran(self, *prefix):
        return any(c[: len(prefix)] == list(prefix) for c in self.calls)


class Precedence(unittest.TestCase):
    def test_ordering_chain(self):
        # The SemVer 2.0 spec's own example ordering.
        chain = ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta", "1.0.0-beta",
                 "1.0.0-beta.2", "1.0.0-beta.11", "1.0.0-rc.1", "1.0.0", "1.0.1", "1.1.0", "2.0.0"]
        for i, a in enumerate(chain):
            for b in chain[i + 1:]:
                self.assertEqual(cr.compare_semver(a, b), -1, (a, b))
                self.assertEqual(cr.compare_semver(b, a), 1, (b, a))

    def test_numeric_not_lexical(self):
        self.assertEqual(cr.compare_semver("1.10.0", "1.9.0"), 1)

    def test_equal_and_build_ignored(self):
        self.assertEqual(cr.compare_semver("1.0.0+a", "1.0.0+b"), 0)

    def test_invalid(self):
        for bad in ["1.0", "beta1", "01.0.0", "1.0.0-", "v1.0.0"]:
            with self.assertRaises(cr.ReleaseError):
                cr.parse_semver(bad)


class ReleaseGuards(unittest.TestCase):
    def go(self, version="1.2.0", push=True, **kw):
        f = FakeRunner(**kw)
        return f, cr.Release(f).release(version, push)

    def fails(self, match, version="1.2.0", **kw):
        f = FakeRunner(**kw)
        with self.assertRaisesRegex(cr.ReleaseError, match):
            cr.Release(f).release(version)
        self.assertFalse(f.ran("git", "tag", "-a"))
        self.assertFalse(f.ran("git", "push"))

    def test_happy_path_pushes_annotated_tag(self):
        f, msg = self.go(local_tags=["v1.1.0"], remote_tags=["v1.1.0"])
        self.assertTrue(f.ran("git", "tag", "-a", "v1.2.0"))
        self.assertTrue(f.ran("git", "push", "origin", "v1.2.0"))
        self.assertIn("pushed", msg)

    def test_no_push(self):
        f, _ = self.go(push=False)
        self.assertTrue(f.ran("git", "tag", "-a", "v1.2.0"))
        self.assertFalse(f.ran("git", "push"))

    def test_dirty_tree(self):
        self.fails("not clean", status="?? new.txt")

    def test_wrong_branch(self):
        self.fails("branch 'dev'", branch="dev")

    def test_head_behind_origin(self):
        self.fails("origin/master", remote="b" * 40)

    def test_invalid_version(self):
        self.fails("SemVer", version="beta1")

    def test_tag_exists_locally(self):
        self.fails("locally", local_tags=["v1.2.0"])

    def test_tag_exists_remote(self):
        self.fails("on origin", remote_tags=["v1.2.0"])

    def test_not_greater(self):
        self.fails("not greater than existing tag v1.3.0", local_tags=["v1.3.0"])

    def test_prerelease_below_stable(self):
        self.fails("not greater", version="1.2.0-rc.1", remote_tags=["v1.2.0"])

    def test_non_semver_tags_ignored(self):
        self.go(local_tags=["vfoo", "v1.1.0"])

    def test_ci_missing(self):
        self.fails("no 'ci / test'", checks=[check("completed", "success", name="other")])

    def test_ci_pending(self):
        self.fails("still in_progress", checks=[check("in_progress", None)])

    def test_ci_failed(self):
        self.fails("concluded failure", checks=[check("completed", "failure")])

    def test_ci_latest_rerun_wins(self):
        self.fails("concluded failure", checks=[check("completed", "success", 1), check("completed", "failure", 2)])


class RepoSlug(unittest.TestCase):
    def test_urls(self):
        for url in ["git@github.com:rfizzle/mod.git", "https://github.com/rfizzle/mod",
                    "https://github.com/rfizzle/mod.git"]:
            self.assertEqual(cr.Release(FakeRunner(origin=url)).repo_slug(), "rfizzle/mod")

    def test_bad(self):
        with self.assertRaises(cr.ReleaseError):
            cr.Release(FakeRunner(origin="/tmp/x")).repo_slug()


class VerifyTag(unittest.TestCase):
    def test_ok_excludes_itself(self):
        f = FakeRunner(remote_tags=["v1.0.0", "v1.2.0"], local_tags=["v1.2.0"])
        self.assertIn("passes", cr.Release(f).verify_tag("v1.2.0"))

    def test_not_on_master(self):
        with self.assertRaisesRegex(cr.ReleaseError, "not on origin/master"):
            cr.Release(FakeRunner(ancestor=False)).verify_tag("v1.2.0")

    def test_older_than_existing(self):
        with self.assertRaisesRegex(cr.ReleaseError, "not greater"):
            cr.Release(FakeRunner(remote_tags=["v2.0.0", "v1.2.0"])).verify_tag("v1.2.0")

    def test_ci_red(self):
        f = FakeRunner(checks=[check("completed", "failure")])
        with self.assertRaisesRegex(cr.ReleaseError, "failure"):
            cr.Release(f).verify_tag("v1.2.0")


class Main(unittest.TestCase):
    def test_exit_codes(self):
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            self.assertEqual(cr.main(["1.2.0", "--no-push"], run=FakeRunner()), 0)
            self.assertEqual(cr.main(["bad"], run=FakeRunner()), 1)
        self.assertIn("error:", err.getvalue())


if __name__ == "__main__":
    unittest.main()
