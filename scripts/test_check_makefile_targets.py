#!/usr/bin/env python3
"""Unit tests for scripts/check-makefile-targets.py.

Hermetic: each test builds a throwaway <root>/<id> member tree, a members.json,
a small contract, and a stand-in hub concord.mk in a temp dir, then drives main().
The fixtures are deliberately tiny and independent of the repo's real
makefile-targets.json and propagate/concord.mk, so a future edit to those cannot
silently change what these assert; a separate RealContract case checks the shipped
files against each other. Run with:

    python3 -m unittest scripts.test_check_makefile_targets
    python3 scripts/test_check_makefile_targets.py
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
    "check_makefile_targets", _HERE / "check-makefile-targets.py"
)
checker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(checker)


CONTRACT = {
    "include": "concord.mk",
    "targets": ["help", "build", "coverage"],
}

HUB_MK = """\
GRADLE ?= ./gradlew
MOD_ID := $(shell awk -F= '/^archives_base_name/ {print $$2}' gradle.properties)

.DEFAULT_GOAL := help
.PHONY: help build coverage

help: ## Show this menu
\t@grep -hE '^[a-z]+:.*## ' $(MAKEFILE_LIST)

build: ## Compile, test, and assemble the mod jar
\t$(GRADLE) build

# A comment between targets belongs to neither recipe.
coverage: ## Merged coverage
\t$(GRADLE) test runGametest jacocoMergedReport
"""

CLEAN_MAKEFILE = """\
include concord.mk

.PHONY: mine

mine: ## A member-specific target
\t$(GRADLE) mine
"""


class CheckMakefileTargets(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)
        self.members = self.root / "members.json"
        self.members.write_text(
            json.dumps({"members": [{"id": "meridian"}]}), encoding="utf-8"
        )
        self.contract = self.root / "makefile-targets.json"
        self.contract.write_text(json.dumps(CONTRACT), encoding="utf-8")
        self.hub = self.root / "hub-concord.mk"
        self.hub.write_text(HUB_MK, encoding="utf-8")
        self.member_dir = self.root / "meridian"
        self.member_dir.mkdir(parents=True)
        self._makefile(CLEAN_MAKEFILE)
        self._shared(HUB_MK)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _makefile(self, text: str) -> None:
        (self.member_dir / "Makefile").write_text(text, encoding="utf-8")

    def _shared(self, text: str) -> None:
        (self.member_dir / "concord.mk").write_text(text, encoding="utf-8")

    def _run(self) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = checker.main(
                [
                    "--root", str(self.root),
                    "--members", str(self.members),
                    "--contract", str(self.contract),
                    "--hub-file", str(self.hub),
                ]
            )
        return code, out.getvalue(), err.getvalue()

    # -- the clean path ------------------------------------------------------

    def test_a_member_that_includes_the_shared_file_passes(self) -> None:
        code, out, err = self._run()
        self.assertEqual(code, 0, err)
        self.assertIn("1 member(s)", out)

    def test_member_specific_targets_are_notes_not_drift(self) -> None:
        code, _, err = self._run()
        self.assertEqual(code, 0, err)
        self.assertIn("mine: member-specific target", err)

    def test_a_dash_include_still_counts(self) -> None:
        self._makefile("-include concord.mk\n")
        code, _, err = self._run()
        self.assertEqual(code, 0, err)

    # -- the include ----------------------------------------------------------

    def test_missing_include_is_drift(self) -> None:
        self._makefile(".PHONY: mine\nmine:\n\t@echo hi\n")
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("does not `include concord.mk`", err)

    def test_including_some_other_file_is_not_enough(self) -> None:
        self._makefile("include other.mk\n")
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("does not `include concord.mk`", err)

    def test_a_commented_out_include_is_drift(self) -> None:
        self._makefile("# include concord.mk\n")
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("does not `include concord.mk`", err)

    # -- the propagated file ---------------------------------------------------

    def test_missing_shared_file_is_drift(self) -> None:
        (self.member_dir / "concord.mk").unlink()
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("concord.mk is missing", err)

    def test_locally_edited_shared_file_is_drift(self) -> None:
        self._shared(HUB_MK + "\n# local tweak\n")
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("differs from the hub's propagate/concord.mk", err)

    # -- redefinition -----------------------------------------------------------

    def test_redefining_an_owned_target_is_drift(self) -> None:
        self._makefile(CLEAN_MAKEFILE + "\nbuild:\n\t$(GRADLE) build -x test\n")
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("build: redefined in the Makefile", err)

    def test_redefining_with_prerequisites_is_drift(self) -> None:
        self._makefile(CLEAN_MAKEFILE + "\ncoverage: build ## mine\n\t@echo x\n")
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("coverage: redefined", err)

    def test_a_double_colon_rule_is_still_a_redefinition(self) -> None:
        self._makefile(CLEAN_MAKEFILE + "\nbuild::\n\t@echo x\n")
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("build: redefined", err)

    def test_one_rule_naming_several_targets_is_caught(self) -> None:
        self._makefile(CLEAN_MAKEFILE + "\nfoo build:\n\t@echo x\n")
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("build: redefined", err)

    def test_variable_assignments_are_not_targets(self) -> None:
        self._makefile(CLEAN_MAKEFILE + "\nbuild := 1\nGRADLE ?= ./gradlew\ntest = x\n")
        code, _, err = self._run()
        self.assertEqual(code, 0, err)

    def test_a_recipe_line_naming_a_target_is_not_a_definition(self) -> None:
        self._makefile(CLEAN_MAKEFILE + "\tbuild: not a rule, it is recipe text\n")
        code, _, err = self._run()
        self.assertEqual(code, 0, err)

    def test_a_continued_variable_is_not_a_rule(self) -> None:
        self._makefile(CLEAN_MAKEFILE + "\nSRC := a \\\n  build:b\n")
        code, _, err = self._run()
        self.assertEqual(code, 0, err)

    # -- the hub file against its contract ---------------------------------------

    def test_a_target_in_the_hub_file_but_not_the_contract_is_drift(self) -> None:
        extra = HUB_MK + "\nextra: ## unlisted\n\t@echo x\n"
        self.hub.write_text(extra, encoding="utf-8")
        self._shared(extra)
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("defines 'extra', which makefile-targets.json does not list", err)

    def test_a_contract_target_the_hub_file_lacks_is_drift(self) -> None:
        contract = dict(CONTRACT, targets=CONTRACT["targets"] + ["ci"])
        self.contract.write_text(json.dumps(contract), encoding="utf-8")
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("lists 'ci', which concord.mk does not define", err)

    # -- degraded inputs ----------------------------------------------------------

    def test_member_not_checked_out_is_a_note(self) -> None:
        self.members.write_text(
            json.dumps({"members": [{"id": "meridian"}, {"id": "ghost"}]}),
            encoding="utf-8",
        )
        code, _, err = self._run()
        self.assertEqual(code, 0, err)
        self.assertIn("skip: ghost not checked out", err)

    def test_no_members_checked_out_passes_with_a_message(self) -> None:
        for path in self.member_dir.iterdir():
            path.unlink()
        self.member_dir.rmdir()
        code, out, _ = self._run()
        self.assertEqual(code, 0)
        self.assertIn("nothing to compare", out)

    def test_member_without_a_makefile_is_a_note(self) -> None:
        (self.member_dir / "Makefile").unlink()
        code, _, err = self._run()
        self.assertEqual(code, 0, err)
        self.assertIn("no Makefile found", err)

    def test_unreadable_makefile_is_a_note_not_a_traceback(self) -> None:
        (self.member_dir / "Makefile").write_bytes(b"\xff\xfe\x00bad")
        code, _, err = self._run()
        self.assertEqual(code, 0, err)
        self.assertIn("unreadable", err)

    def test_missing_hub_file_exits_two(self) -> None:
        self.hub.unlink()
        with self.assertRaises(SystemExit) as raised:
            self._run()
        self.assertEqual(raised.exception.code, 2)

    def test_missing_contract_exits_two(self) -> None:
        self.contract.unlink()
        with self.assertRaises(SystemExit) as raised:
            self._run()
        self.assertEqual(raised.exception.code, 2)

    def test_malformed_contract_json_exits_two(self) -> None:
        self.contract.write_text("{ not json", encoding="utf-8")
        with self.assertRaises(SystemExit) as raised:
            self._run()
        self.assertEqual(raised.exception.code, 2)

    def test_contract_without_targets_exits_two(self) -> None:
        self.contract.write_text(json.dumps({"include": "concord.mk"}), encoding="utf-8")
        with self.assertRaises(SystemExit) as raised:
            self._run()
        self.assertEqual(raised.exception.code, 2)

    def test_contract_listing_a_target_twice_exits_two(self) -> None:
        self.contract.write_text(
            json.dumps({"include": "concord.mk", "targets": ["build", "build"]}),
            encoding="utf-8",
        )
        with self.assertRaises(SystemExit) as raised:
            self._run()
        self.assertEqual(raised.exception.code, 2)

    def test_member_entry_without_an_id_exits_two(self) -> None:
        self.members.write_text(
            json.dumps({"members": [{"name": "nameless"}]}), encoding="utf-8"
        )
        with self.assertRaises(SystemExit) as raised:
            self._run()
        self.assertEqual(raised.exception.code, 2)


class RealContract(unittest.TestCase):
    """Sanity-check the contract and hub file this repo actually ships."""

    def setUp(self) -> None:
        self.contract = checker.load_contract(_HERE.parent / "makefile-targets.json")
        self.hub_text = (_HERE.parent / "propagate" / self.contract["include"]).read_text(
            encoding="utf-8"
        )

    def test_the_contract_and_the_hub_file_list_the_same_targets(self) -> None:
        self.assertEqual(checker.check_hub(self.contract, self.hub_text), [])

    def test_the_universal_targets_are_present(self) -> None:
        self.assertGreaterEqual(
            set(self.contract["targets"]),
            {"help", "build", "jar", "test", "coverage", "ci", "run-client",
             "run-server", "run-datagen", "gen-sources", "refresh-deps", "clean",
             "version", "release", "site", "site-serve", "sync"},
        )

    def test_the_hub_file_defines_the_default_goal_and_a_phony_for_every_target(self) -> None:
        self.assertIn(".DEFAULT_GOAL := help", self.hub_text)
        phony = next(
            line for line in self.hub_text.splitlines() if line.startswith(".PHONY:")
        ).split()[1:]
        self.assertEqual(set(phony), set(self.contract["targets"]))

    def test_release_calls_the_propagated_release_script(self) -> None:
        self.assertIn("python3 scripts/concord-release.py $(VERSION)", self.hub_text)

    def test_ci_runs_the_workflow_gradle_steps_in_order(self) -> None:
        workflow = (_HERE.parent / ".github" / "workflows" / "mod-ci.yml").read_text(
            encoding="utf-8"
        )
        gradle_steps = [
            line.split("run: ", 1)[1].strip()
            for line in workflow.splitlines()
            if "run: ./gradlew" in line
        ]
        ci_steps = [
            line.strip().replace("$(GRADLE)", "./gradlew")
            for line in self.hub_text.splitlines()
            if line.strip().startswith("$(GRADLE)")
        ]
        # The workflow's gradle commands, in order, must appear in `ci` in that order.
        ci_recipe = ci_steps[ci_steps.index("./gradlew build --no-daemon --stacktrace --warning-mode=all"):]
        self.assertEqual(ci_recipe[: len(gradle_steps)], gradle_steps)


if __name__ == "__main__":
    unittest.main()
