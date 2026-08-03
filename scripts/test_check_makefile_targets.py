#!/usr/bin/env python3
"""Unit tests for scripts/check-makefile-targets.py.

Hermetic: each test builds a throwaway <root>/<id> member tree, a members.json,
and a small contract in a temp dir, then drives main(). The contract fixture is
deliberately tiny and independent of the repo's real makefile-targets.json, so a
future edit to the real contract cannot silently change what these assert; a
separate RealContract case checks the shipped file. Run with:

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
    "helpPreamble": '\t@echo "Targets:"',
    "helpOrder": ["build", "jar", "coverage"],
    "universal": [
        {
            "target": "build",
            "help": "Compile, test, and assemble the mod jar",
            "recipe": ["\t$(GRADLE) build"],
        },
        {
            "target": "jar",
            "prerequisites": "build",
            "help": "Print the path to the built primary jar",
            "recipe": ["\t@ls -1 build/libs/{modid}-*.jar | head -1"],
        },
    ],
    "conditional": [
        {
            "target": "coverage",
            "help": "Run unit tests + gametests and write the merged coverage report",
            "recipe": ["\t$(GRADLE) test runGametest jacocoMergedReport"],
            "requiredWhen": {"file": "build.gradle", "contains": "jacocoMergedReport"},
            "because": "the documented local entry point would be missing.",
        }
    ],
}

CLEAN_MAKEFILE = """\
GRADLE := ./gradlew

.PHONY: help build jar coverage

help:
\t@echo "Targets:"
\t@echo "  build        Compile, test, and assemble the mod jar"
\t@echo "  jar          Print the path to the built primary jar"
\t@echo "  coverage     Run unit tests + gametests and write the merged coverage report"

build:
\t$(GRADLE) build

jar: build
\t@ls -1 build/libs/meridian-*.jar | head -1

# A comment between targets belongs to neither recipe.
coverage:
\t$(GRADLE) test runGametest jacocoMergedReport
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
        self.member_dir = self.root / "meridian"
        self.member_dir.mkdir(parents=True)
        self._makefile(CLEAN_MAKEFILE)
        self._build_gradle(wired=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _makefile(self, text: str) -> None:
        (self.member_dir / "Makefile").write_text(text, encoding="utf-8")

    def _build_gradle(self, wired: bool) -> None:
        body = (
            "tasks.register('jacocoMergedReport', JacocoReport) { }"
            if wired
            else "// no coverage wiring here"
        )
        (self.member_dir / "build.gradle").write_text(body, encoding="utf-8")

    def _run(self) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = checker.main(
                [
                    "--root", str(self.root),
                    "--members", str(self.members),
                    "--contract", str(self.contract),
                ]
            )
        return code, out.getvalue(), err.getvalue()

    # --- the conformant baseline -------------------------------------------

    def test_conforming_makefile_passes_with_no_findings(self) -> None:
        code, out, err = self._run()
        self.assertEqual(code, 0, err)
        self.assertEqual(err, "")
        self.assertIn("match the target contract", out)

    def test_modid_token_is_substituted_per_member(self) -> None:
        """{modid} resolves to the member id, so the jar glob is not drift."""
        code, _, err = self._run()
        self.assertEqual(code, 0, err)
        self.assertNotIn("jar:", err)

    def test_comment_between_targets_is_not_part_of_a_recipe(self) -> None:
        """The clean fixture has a comment above coverage; it must not count."""
        code, _, err = self._run()
        self.assertEqual(code, 0, err)
        self.assertNotIn("recipe differs", err)

    # --- universal targets --------------------------------------------------

    def test_missing_universal_target_is_drift(self) -> None:
        self._makefile(CLEAN_MAKEFILE.replace("build:\n\t$(GRADLE) build\n\n", ""))
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("build: target is missing", err)

    def test_changed_recipe_is_drift(self) -> None:
        self._makefile(CLEAN_MAKEFILE.replace("$(GRADLE) build", "$(GRADLE) assemble"))
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("build: recipe differs from the contract", err)

    def test_changed_prerequisites_is_drift(self) -> None:
        self._makefile(CLEAN_MAKEFILE.replace("jar: build", "jar:"))
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("jar: prerequisites are ''", err)

    # --- conditional targets ------------------------------------------------

    def test_conditional_target_missing_while_wired_is_drift(self) -> None:
        """tribulation/respite: jacocoMergedReport wired, no coverage target."""
        self._makefile(
            CLEAN_MAKEFILE.replace(
                "coverage:\n\t$(GRADLE) test runGametest jacocoMergedReport\n", ""
            ).replace(
                '\t@echo "  coverage     Run unit tests + gametests and write the merged coverage report"\n',
                "",
            ).replace(".PHONY: help build jar coverage", ".PHONY: help build jar")
        )
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("coverage: target is missing while build.gradle", err)
        self.assertIn("documented local entry point", err)

    def test_conditional_target_missing_while_unwired_is_a_note(self) -> None:
        """mercantile: no datagen wiring, so no target owed."""
        self._build_gradle(wired=False)
        self._makefile(
            CLEAN_MAKEFILE.replace(
                "coverage:\n\t$(GRADLE) test runGametest jacocoMergedReport\n", ""
            ).replace(
                '\t@echo "  coverage     Run unit tests + gametests and write the merged coverage report"\n',
                "",
            ).replace(".PHONY: help build jar coverage", ".PHONY: help build jar")
        )
        code, _, err = self._run()
        self.assertEqual(code, 0, err)
        self.assertIn("coverage: absent, and not wired in this member", err)

    def test_missing_build_gradle_leaves_conditional_unowed(self) -> None:
        (self.member_dir / "build.gradle").unlink()
        self._makefile(
            CLEAN_MAKEFILE.replace(
                "coverage:\n\t$(GRADLE) test runGametest jacocoMergedReport\n", ""
            ).replace(
                '\t@echo "  coverage     Run unit tests + gametests and write the merged coverage report"\n',
                "",
            ).replace(".PHONY: help build jar coverage", ".PHONY: help build jar")
        )
        code, _, err = self._run()
        self.assertEqual(code, 0, err)

    # --- help ---------------------------------------------------------------

    def test_reworded_help_description_is_drift(self) -> None:
        """mercantile/cultivation: three wordings of the coverage line."""
        self._makefile(
            CLEAN_MAKEFILE.replace(
                "write the merged coverage report",
                "build the merged JaCoCo report",
            )
        )
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("help: describes coverage as", err)

    def test_help_listing_an_undefined_target_is_drift(self) -> None:
        """A help menu advertising a target nobody can run."""
        self._makefile(
            CLEAN_MAKEFILE.replace(
                '\t@echo "  coverage ',
                '\t@echo "  run-datagen  Run Fabric data generation"\n'
                '\t@echo "  coverage ',
                1,
            )
        )
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn(
            "help: lists run-datagen, which this Makefile does not define", err
        )

    def test_help_omitting_a_defined_target_is_drift(self) -> None:
        self._makefile(
            CLEAN_MAKEFILE.replace(
                '\t@echo "  jar          Print the path to the built primary jar"\n', ""
            )
        )
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("help: does not list jar", err)

    def test_help_out_of_canonical_order_is_drift(self) -> None:
        self._makefile(
            CLEAN_MAKEFILE.replace(
                '\t@echo "  build        Compile, test, and assemble the mod jar"\n'
                '\t@echo "  jar          Print the path to the built primary jar"\n',
                '\t@echo "  jar          Print the path to the built primary jar"\n'
                '\t@echo "  build        Compile, test, and assemble the mod jar"\n',
            )
        )
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("help: lists targets in the order", err)

    def test_missing_help_target_is_drift(self) -> None:
        self._makefile(
            CLEAN_MAKEFILE[CLEAN_MAKEFILE.index("build:"):]
        )
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("help: target is missing", err)

    # --- .PHONY -------------------------------------------------------------

    def test_target_absent_from_phony_is_drift(self) -> None:
        self._makefile(
            CLEAN_MAKEFILE.replace(".PHONY: help build jar coverage", ".PHONY: help build jar")
        )
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("shadows the target", err)

    def test_no_phony_declaration_is_drift(self) -> None:
        self._makefile(CLEAN_MAKEFILE.replace(".PHONY: help build jar coverage\n", ""))
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("no .PHONY declaration", err)

    # --- notes, which must not fail the run ---------------------------------

    def test_extra_target_is_a_note_not_drift(self) -> None:
        self._makefile(
            CLEAN_MAKEFILE.replace(".PHONY: help build jar coverage",
                                   ".PHONY: help build jar coverage bootstrap")
            + "\nbootstrap:\n\t./scripts/bootstrap.sh\n"
        )
        code, _, err = self._run()
        self.assertEqual(code, 0, err)
        self.assertIn("bootstrap: target is not in the contract", err)

    def test_missing_makefile_is_a_note(self) -> None:
        (self.member_dir / "Makefile").unlink()
        code, _, err = self._run()
        self.assertEqual(code, 0, err)
        self.assertIn("no Makefile found", err)

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

    def test_malformed_contract_exits_two(self) -> None:
        self.contract.write_text("{ not json", encoding="utf-8")
        with self.assertRaises(SystemExit) as raised:
            self._run()
        self.assertEqual(raised.exception.code, 2)

    def test_contract_missing_a_required_key_exits_two(self) -> None:
        self.contract.write_text(json.dumps({"universal": []}), encoding="utf-8")
        with self.assertRaises(SystemExit) as raised:
            self._run()
        self.assertEqual(raised.exception.code, 2)


class RealContract(unittest.TestCase):
    """Sanity-check the contract this repo actually ships."""

    def setUp(self) -> None:
        self.contract = checker.load_contract(
            _HERE.parent / "makefile-targets.json"
        )

    def test_universal_targets_are_the_documented_thirteen(self) -> None:
        names = {spec["target"] for spec in self.contract["universal"]}
        self.assertEqual(
            names,
            {"build", "jar", "test", "run-client", "run-server", "gen-sources",
             "refresh-deps", "clean", "version", "release", "site", "site-serve",
             "sync"},
        )

    def test_conditional_targets_are_coverage_and_run_datagen(self) -> None:
        names = {spec["target"] for spec in self.contract["conditional"]}
        self.assertEqual(names, {"coverage", "run-datagen"})

    def test_every_governed_target_has_a_help_string_and_recipe(self) -> None:
        for spec in self.contract["universal"] + self.contract["conditional"]:
            self.assertTrue(spec.get("help"), spec["target"])
            self.assertTrue(spec.get("recipe"), spec["target"])

    def test_every_conditional_target_states_its_condition_and_reason(self) -> None:
        for spec in self.contract["conditional"]:
            self.assertIn("file", spec["requiredWhen"])
            self.assertIn("contains", spec["requiredWhen"])
            self.assertTrue(spec.get("because"), spec["target"])

    def test_help_order_covers_every_governed_target(self) -> None:
        governed = {
            spec["target"]
            for spec in self.contract["universal"] + self.contract["conditional"]
        }
        self.assertEqual(set(self.contract["helpOrder"]), governed)


if __name__ == "__main__":
    unittest.main()
