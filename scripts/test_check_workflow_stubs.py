#!/usr/bin/env python3
"""Unit tests for scripts/check-workflow-stubs.py.

Hermetic: each test builds a throwaway <root>/<id> member tree plus a small
manifest and members.json in a temp dir, then drives main(). Run with:

    python3 -m unittest scripts.test_check_workflow_stubs
    python3 scripts/test_check_workflow_stubs.py
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
    "check_workflow_stubs", _HERE / "check-workflow-stubs.py"
)
checker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(checker)


MANIFEST = {
    "stubs": [
        {
            "member": "ci.yml",
            "reusable": "mod-ci.yml",
            "uses": "rfizzle/concord/.github/workflows/mod-ci.yml@master",
            "permissions": {
                "contents": "read",
                "checks": "write",
                "pull-requests": "write",
            },
        },
        {
            "member": "release.yml",
            "reusable": "mod-release.yml",
            "uses": "rfizzle/concord/.github/workflows/mod-release.yml@master",
            "permissions": {"contents": "write", "pull-requests": "write"},
        },
    ]
}


def _stub_yaml(perms: dict, uses: str, *, extras: str = "") -> str:
    """A minimal caller-stub YAML. `extras` is an optional pre-indented block
    (e.g. a `with:` section at 4-space job indent) inserted under the job."""
    lines = [
        "name: Stub",
        "on:",
        "  push:",
        "    branches: [master]",
        "permissions:",
        *(f"  {k}: {v}" for k, v in perms.items()),
        "jobs:",
        "  job:",
        f"    uses: {uses}",
    ]
    return "\n".join(lines) + "\n" + extras + "    secrets: inherit\n"


class CheckWorkflowStubs(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)
        self.manifest = self.root / "workflow-stubs.json"
        self.manifest.write_text(json.dumps(MANIFEST), encoding="utf-8")
        self.members = self.root / "members.json"
        self.members.write_text(
            json.dumps({"members": [{"id": "meridian"}]}), encoding="utf-8"
        )
        self.wf_dir = self.root / "meridian" / ".github" / "workflows"
        self.wf_dir.mkdir(parents=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self, name: str, content: str) -> None:
        (self.wf_dir / name).write_text(content, encoding="utf-8")

    def _write_correct(self) -> None:
        for stub in MANIFEST["stubs"]:
            self._write(stub["member"], _stub_yaml(stub["permissions"], stub["uses"]))

    def _run(self) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = checker.main(
                [
                    "--root",
                    str(self.root),
                    "--manifest",
                    str(self.manifest),
                    "--members",
                    str(self.members),
                ]
            )
        return code, out.getvalue(), err.getvalue()

    def test_clean_passes(self) -> None:
        self._write_correct()
        code, out, err = self._run()
        self.assertEqual(code, 0, err)
        self.assertIn("all workflow stubs match", out)

    def test_extra_permission_is_drift(self) -> None:
        self._write_correct()
        perms = dict(MANIFEST["stubs"][0]["permissions"], **{"issues": "read"})
        self._write("ci.yml", _stub_yaml(perms, MANIFEST["stubs"][0]["uses"]))
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("unexpected 'issues: read'", err)
        self.assertIn("widens the token", err)

    def test_missing_permission_is_drift(self) -> None:
        self._write_correct()
        self._write(
            "release.yml",
            _stub_yaml(
                {"contents": "write"},  # dropped pull-requests: write
                MANIFEST["stubs"][1]["uses"],
            ),
        )
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("missing 'pull-requests: write'", err)

    def test_wrong_uses_ref_is_drift(self) -> None:
        self._write_correct()
        self._write(
            "ci.yml",
            _stub_yaml(
                MANIFEST["stubs"][0]["permissions"],
                "rfizzle/concord/.github/workflows/mod-ci.yml@v1",
            ),
        )
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("@v1", err)
        self.assertIn("expected", err)

    def test_missing_stub_file_is_drift(self) -> None:
        self._write_correct()
        (self.wf_dir / "release.yml").unlink()
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("missing stub file", err)

    def test_malformed_yaml_is_drift_not_crash(self) -> None:
        self._write_correct()
        self._write("ci.yml", "permissions: [unterminated\n")
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("malformed YAML", err)

    def test_per_repo_variation_ignored(self) -> None:
        self._write_correct()
        # Correct perms + uses, but extra with: inputs and different triggers.
        stub = MANIFEST["stubs"][1]
        yaml_with_inputs = _stub_yaml(
            stub["permissions"],
            stub["uses"],
            extras='    with:\n      curseforge-id: "1546092"\n      modrinth-id: "qywREjYt"\n',
        )
        self._write("release.yml", yaml_with_inputs)
        code, _, err = self._run()
        self.assertEqual(code, 0, err)

    def test_unknown_concord_stub_is_note_not_failure(self) -> None:
        self._write_correct()
        self._write(
            "rogue.yml",
            _stub_yaml(
                {"contents": "read"},
                "rfizzle/concord/.github/workflows/mod-ci.yml@master",
            ),
        )
        code, _, err = self._run()
        self.assertEqual(code, 0, err)
        self.assertIn("not in the manifest", err)

    def test_scalar_permissions_is_drift(self) -> None:
        self._write_correct()
        self._write(
            "ci.yml",
            "name: Stub\non:\n  push:\n    branches: [master]\n"
            "permissions: write-all\njobs:\n  job:\n"
            "    uses: rfizzle/concord/.github/workflows/mod-ci.yml@master\n",
        )
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("write-all", err)

    def test_empty_doc_is_drift_not_crash(self) -> None:
        self._write_correct()
        self._write("ci.yml", "")  # yaml.safe_load("") -> None
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("top level is not a mapping", err)

    def test_job_level_permissions_override_is_checked(self) -> None:
        self._write_correct()
        # Top-level permissions are correct, but a job-level block adds issues:
        # read — the effective grant for the reusable call, so it must be caught.
        self._write(
            "ci.yml",
            "name: Stub\non:\n  push:\n    branches: [master]\n"
            "permissions:\n  contents: read\n  checks: write\n  pull-requests: write\n"
            "jobs:\n  job:\n"
            "    permissions:\n      contents: read\n      checks: write\n"
            "      pull-requests: write\n      issues: read\n"
            "    uses: rfizzle/concord/.github/workflows/mod-ci.yml@master\n",
        )
        code, _, err = self._run()
        self.assertEqual(code, 1)
        self.assertIn("unexpected 'issues: read'", err)

    def test_malformed_manifest_exits_2(self) -> None:
        bad = self.root / "bad.json"
        bad.write_text("{ not json", encoding="utf-8")
        with self.assertRaises(SystemExit) as cm:
            checker.main(
                [
                    "--root",
                    str(self.root),
                    "--manifest",
                    str(bad),
                    "--members",
                    str(self.members),
                ]
            )
        self.assertEqual(cm.exception.code, 2)

    def test_no_members_checked_out_passes(self) -> None:
        self.members.write_text(
            json.dumps({"members": [{"id": "absent"}]}), encoding="utf-8"
        )
        code, out, err = self._run()
        self.assertEqual(code, 0)
        self.assertIn("not checked out", err)


class RealManifest(unittest.TestCase):
    def test_repo_manifest_parses_and_is_complete(self) -> None:
        repo_root = _HERE.parent
        stubs = checker.load_manifest(repo_root / "workflow-stubs.json")
        names = {s["member"] for s in stubs}
        # The eight member caller stubs the suite ships.
        self.assertEqual(
            names,
            {
                "ci.yml",
                "release.yml",
                "listing-sync.yml",
                "site.yml",
                "build-artifact.yml",
                "claude-code-review.yml",
                "claude-spec.yml",
                "claude.yml",
            },
        )
        for stub in stubs:
            self.assertTrue(stub["uses"].startswith(checker.CONCORD_PREFIX))
            self.assertIsInstance(stub["permissions"], dict)
            self.assertTrue(stub["permissions"])


if __name__ == "__main__":
    unittest.main()
