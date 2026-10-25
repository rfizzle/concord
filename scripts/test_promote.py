#!/usr/bin/env python3
"""Unit tests for scripts/promote.py.

Hermetic: the git/gh/unit-test helpers and the clock are replaced with a scripted
fake, so no repo, network or sleeping is involved. Run with:

    python3 -m unittest scripts.test_promote
    python3 scripts/test_promote.py
"""

from __future__ import annotations

import datetime
import importlib.util
import io
import json
import pathlib
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

_HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("promote", _HERE / "promote.py")
promote = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(promote)

STABLE = "a" * 40
TARGET = "b" * 40
BASE = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)


class Fake:
    """Scripted stand-in for git, gh, the unit-test runner and the clock."""

    def __init__(self) -> None:
        self.t = 0.0
        self.stable: str | None = STABLE
        self.target = TARGET
        self.ff = True
        self.check_runs = [{"name": "Site", "status": "completed", "conclusion": "success"}]
        self.sync_prs: list[dict] = []
        self.test_failures: list[str] = []
        self.head = TARGET
        self.dirty = ""
        self.master = TARGET
        self.propagate_runs = [{"status": "completed", "conclusion": "success", "url": "https://example.test/p/1"}]
        self.ci_conclusion = "success"
        self.ci_polls_to_finish = 2  # polls with status in_progress before completing
        self.calls: list[tuple] = []
        self._polls = 0
        self._dispatched_at: float | None = None

    # clock
    def now(self):
        return BASE + datetime.timedelta(seconds=self.t)

    def monotonic(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += seconds

    # git
    def git(self, *args, check=True):
        self.calls.append(("git", *args))
        if args[0] == "fetch":
            return ""
        if args[0] == "status":
            return self.dirty
        if args[0] == "rev-parse":
            if args[1:] == ("HEAD",):
                return self.head
            if args[1:] == ("origin/master",):
                return self.master
            if "origin/stable^{commit}" in args:
                return self.stable or ""
            return self.target
        if args[0] == "log":
            return "bbbbbbb feat: one\nccccccc fix: two"
        if args[0] == "push":
            return ""
        raise AssertionError(args)

    def git_ok(self, *args):
        self.calls.append(("git", *args))
        return self.ff

    # gh
    def gh(self, *args):
        self.calls.append(("gh", *args))
        if args[0] == "api":
            return "".join(json.dumps(r) + "\n" for r in self.check_runs)
        if args[0] == "pr":
            return json.dumps(self.sync_prs)
        if args[0] == "workflow":
            self._dispatched_at = self.t
            return ""
        if args[0] == "run" and "propagate.yml" in args:
            return json.dumps(self.propagate_runs)
        if args[0] == "run":
            if self._dispatched_at is None:
                return "[]"
            self._polls += 1
            done = self._polls > self.ci_polls_to_finish
            created = (BASE + datetime.timedelta(seconds=self._dispatched_at + 1)).isoformat()
            return json.dumps(
                [
                    {
                        "databaseId": 7,
                        "createdAt": created.replace("+00:00", "Z"),
                        "status": "completed" if done else "in_progress",
                        "conclusion": self.ci_conclusion if done else "",
                        "url": "https://example.test/run/7",
                    },
                    {  # an older dispatch that must be ignored
                        "databaseId": 3,
                        "createdAt": (BASE - datetime.timedelta(days=1)).isoformat().replace("+00:00", "Z"),
                        "status": "completed",
                        "conclusion": "failure",
                        "url": "https://example.test/run/3",
                    },
                ]
            )
        raise AssertionError(args)

    def run_unit_tests(self, modules):
        self.calls.append(("tests", tuple(modules)))
        return self.test_failures

    def pushes(self) -> list[tuple]:
        return [c for c in self.calls if c[:2] == ("git", "push")]


class PromoteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fake = Fake()
        f = self.fake
        patches = [
            mock.patch.object(promote, "git", f.git),
            mock.patch.object(promote, "git_ok", f.git_ok),
            mock.patch.object(promote, "gh", f.gh),
            mock.patch.object(promote, "run_unit_tests", f.run_unit_tests),
            mock.patch.object(promote, "now", f.now),
            mock.patch.object(promote, "monotonic", f.monotonic),
            mock.patch.object(promote, "sleep", f.sleep),
            mock.patch.object(promote, "canary_members", lambda: ["instinct"]),
            mock.patch.object(promote, "test_modules", lambda: ["scripts.test_x"]),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def run_main(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = promote.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_missing_stable_fails_with_creation_hint(self) -> None:
        self.fake.stable = None
        code, _, err = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("git push origin <sha>:refs/heads/stable", err)
        self.assertEqual(self.fake.pushes(), [])

    def test_already_promoted_exits_zero(self) -> None:
        self.fake.target = STABLE
        code, out, _ = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn("stable is already at", out)
        self.assertEqual(self.fake.pushes(), [])

    def test_non_fast_forward_fails(self) -> None:
        self.fake.ff = False
        code, _, err = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("only fast-forwards", err)
        self.assertEqual(self.fake.pushes(), [])

    def test_failing_hub_check_run_fails(self) -> None:
        self.fake.check_runs.append({"name": "Catalog", "status": "completed", "conclusion": "failure"})
        code, _, err = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("Catalog", err)
        self.assertEqual(self.fake.pushes(), [])

    def test_unfinished_hub_check_run_fails(self) -> None:
        self.fake.check_runs = [{"name": "Site", "status": "in_progress", "conclusion": None}]
        code, _, err = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("in_progress", err)

    def test_no_hub_check_runs_is_fine(self) -> None:
        self.fake.check_runs = []
        code, _, err = self.run_main()
        self.assertEqual(code, 0, err)

    def test_failing_unit_tests_fail(self) -> None:
        self.fake.test_failures = ["scripts.test_x"]
        code, _, err = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("scripts.test_x", err)
        self.assertEqual(self.fake.pushes(), [])

    def test_open_sync_pr_on_canary_fails(self) -> None:
        self.fake.sync_prs = [{"url": "https://example.test/pr/1", "headRefName": "concord-sync"}]
        code, _, err = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("https://example.test/pr/1", err)
        self.assertNotIn(("gh", "workflow"), [c[:2] for c in self.fake.calls])

    def test_failed_canary_ci_fails(self) -> None:
        self.fake.ci_conclusion = "failure"
        code, _, err = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("instinct CI concluded failure", err)
        self.assertEqual(self.fake.pushes(), [])

    def test_timed_out_canary_ci_fails(self) -> None:
        self.fake.ci_polls_to_finish = 10**9
        code, _, err = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("timed out", err)
        self.assertEqual(self.fake.pushes(), [])

    def test_dry_run_does_not_push(self) -> None:
        code, out, err = self.run_main("--dry-run")
        self.assertEqual(code, 0, err)
        self.assertIn("dry run", out)
        self.assertEqual(self.fake.pushes(), [])

    def test_happy_path_pushes_the_target_to_stable(self) -> None:
        code, out, err = self.run_main()
        self.assertEqual(code, 0, err)
        self.assertEqual(self.fake.pushes(), [("git", "push", "origin", f"{TARGET}:refs/heads/stable")])
        self.assertIn("instinct CI green on master", out)
        self.assertIn("feat: one", out)

    def test_checkout_not_at_target_fails(self) -> None:
        self.fake.head = STABLE
        code, _, err = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("check out", err)
        self.assertNotIn(("tests",), [c[:1] for c in self.fake.calls])

    def test_dirty_tree_fails(self) -> None:
        self.fake.dirty = " M scripts/promote.py"
        code, _, err = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("not clean", err)

    def test_unfinished_propagate_run_fails(self) -> None:
        self.fake.propagate_runs.insert(0, {"status": "in_progress", "conclusion": "", "url": "https://example.test/p/2"})
        code, _, err = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("https://example.test/p/2", err)
        self.assertNotIn(("gh", "workflow"), [c[:2] for c in self.fake.calls])

    def test_failed_latest_propagate_run_fails(self) -> None:
        self.fake.propagate_runs[0]["conclusion"] = "failure"
        code, _, err = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("propagate run concluded failure", err)

    def test_target_behind_master_notes_what_the_canary_runs(self) -> None:
        self.fake.master = "c" * 40
        code, out, err = self.run_main()
        self.assertEqual(code, 0, err)
        self.assertIn("the canary CI below runs that", out)

    def test_canary_ci_is_dispatched_on_master(self) -> None:
        self.run_main()
        self.assertIn(
            ("gh", "workflow", "run", "ci.yml", "-R", "rfizzle/instinct", "--ref", "master"),
            self.fake.calls,
        )


if __name__ == "__main__":
    unittest.main()
