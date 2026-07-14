#!/usr/bin/env python3
"""Tests for scripts/sync-labels.py.

Two layers:

  * Integration — drive the script against a mock `gh` that serves a synthetic
    member's label list and records the create/update calls, asserting the sync
    semantics that matter: create-missing, update-drift, in-sync-noop, extra
    labels never touched, and case-insensitive recase-in-place. The script reads
    the real ./labels.json, so each test derives its member state from that
    manifest and perturbs it — the assertions track the shipped label set.

  * Validation — import load_manifest() and confirm it accepts the real manifest
    and rejects malformed ones (a bad manifest must fail loudly, since it would
    otherwise propagate garbage to every member).
"""
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest

ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                      capture_output=True, text=True, check=True).stdout.strip()


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "sync_labels", os.path.join(ROOT, "scripts", "sync-labels.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sync_labels = _load_module()
MANIFEST = json.load(open(os.path.join(ROOT, "labels.json"), encoding="utf-8"))["labels"]


# A standalone `gh` replacement. Serves the labels in $MEMBER_STATE and appends
# each mutating call to $ACTIONS_LOG as one JSON object per line.
GH_MOCK = r'''#!/usr/bin/env python3
import json, os, sys, urllib.parse
STATE = json.load(open(os.environ["MEMBER_STATE"]))
def log(a):
    open(os.environ["ACTIONS_LOG"], "a").write(json.dumps(a) + "\n")
def parse(argv):
    method, endpoint, fields = "GET", None, {}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "-X": method = argv[i+1]; i += 2; continue
        if a in ("-f", "-F"):
            k, _, v = argv[i+1].partition("="); fields[k] = v; i += 2; continue
        if endpoint is None and not a.startswith("-"): endpoint = a
        i += 1
    return method, endpoint, fields
argv = sys.argv[1:]           # drop the leading "api"
method, endpoint, fields = parse(argv[1:])
base = endpoint.split("?", 1)[0] if endpoint else ""
if base.endswith("/labels") and method == "GET":
    page = 1
    if "?" in endpoint:
        for kv in endpoint.split("?", 1)[1].split("&"):
            if kv.startswith("page="): page = int(kv.split("=", 1)[1])
    sys.stdout.write(json.dumps(STATE["labels"] if page == 1 else []))
    sys.exit(0)
if base.endswith("/labels") and method == "POST":
    if fields["name"] in STATE.get("conflict", []):
        # Simulate a create that races an existing label — GitHub answers 422.
        sys.stdout.write(json.dumps({"message": "Validation Failed",
                                     "errors": [{"code": "already_exists"}]}))
        sys.exit(1)
    log({"action": "create", "name": fields["name"], "color": fields["color"],
         "description": fields.get("description", "")})
    sys.stdout.write("{}"); sys.exit(0)
if "/labels/" in base and method == "PATCH":
    log({"action": "update", "path": urllib.parse.unquote(base.split("/labels/", 1)[1]),
         "new_name": fields.get("new_name"), "color": fields["color"],
         "description": fields.get("description", "")})
    sys.stdout.write("{}"); sys.exit(0)
sys.stderr.write("gh mock: unhandled " + str(endpoint) + " " + method + "\n"); sys.exit(3)
'''


def _clone(manifest):
    return [dict(label) for label in manifest]


class SyncLabelsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.gh = os.path.join(self.tmp, "gh")
        with open(self.gh, "w") as f:
            f.write(GH_MOCK)
        os.chmod(self.gh, 0o755)

    def run_sync(self, labels, conflict=None):
        state_path = os.path.join(self.tmp, "member_state.json")
        log_path = os.path.join(self.tmp, "actions.log")
        with open(state_path, "w") as f:
            json.dump({"labels": labels, "conflict": conflict or []}, f)
        if os.path.exists(log_path):
            os.remove(log_path)
        env = dict(os.environ)
        env["PATH"] = self.tmp + os.pathsep + env["PATH"]
        env["MEMBER_STATE"] = state_path
        env["ACTIONS_LOG"] = log_path
        env["GH_TOKEN"] = "x"
        env["SYNC_LABELS_MAX_ATTEMPTS"] = "1"
        p = subprocess.run(["python3", "scripts/sync-labels.py", "rfizzle/testmember"],
                           cwd=ROOT, env=env, capture_output=True, text=True)
        actions = []
        if os.path.exists(log_path):
            with open(log_path) as f:
                actions = [json.loads(l) for l in f]
        return p, {
            "create": {a["name"]: a for a in actions if a["action"] == "create"},
            "update": {a["path"]: a for a in actions if a["action"] == "update"},
        }

    def test_creates_missing_label(self):
        state = [l for l in _clone(MANIFEST) if l["name"] != "jules"]
        p, a = self.run_sync(state)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("jules", a["create"])
        self.assertEqual(a["create"]["jules"]["color"],
                         next(l["color"] for l in MANIFEST if l["name"] == "jules"))
        self.assertEqual(len(a["create"]), 1, "only the missing label is created")
        self.assertFalse(a["update"], "matching labels are not updated")

    def test_updates_drifted_label(self):
        state = _clone(MANIFEST)
        target = next(l for l in state if l["name"] == "ready")
        target["color"] = "000000"
        target["description"] = "stale wording"
        p, a = self.run_sync(state)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse(a["create"])
        self.assertIn("ready", a["update"])
        want = next(l for l in MANIFEST if l["name"] == "ready")
        self.assertEqual(a["update"]["ready"]["color"], want["color"])
        self.assertEqual(a["update"]["ready"]["description"], want["description"])
        self.assertEqual(len(a["update"]), 1, "only the drifted label is updated")

    def test_in_sync_writes_nothing(self):
        p, a = self.run_sync(_clone(MANIFEST))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse(a["create"])
        self.assertFalse(a["update"])
        self.assertIn("in sync", p.stdout)

    def test_extra_label_is_never_touched(self):
        state = _clone(MANIFEST) + [
            {"name": "wontfix", "color": "ffffff", "description": "This will not be worked on"}]
        p, a = self.run_sync(state)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn("wontfix", a["create"])
        self.assertNotIn("wontfix", a["update"])
        self.assertFalse(a["create"])
        self.assertFalse(a["update"])

    def test_create_conflict_falls_through_to_update(self):
        # jules is absent from the member, so the script tries to create it — but
        # the create races and GitHub returns 422 already-exists. The run must
        # reconcile it with a PATCH and still exit 0, not abort the member.
        state = [l for l in _clone(MANIFEST) if l["name"] != "jules"]
        p, a = self.run_sync(state, conflict=["jules"])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn("jules", a["create"], "the raced create is not logged as a success")
        self.assertIn("jules", a["update"], "a 422 create must fall through to a PATCH")
        self.assertEqual(a["update"]["jules"]["new_name"], "jules")

    def test_case_insensitive_recase_in_place(self):
        state = _clone(MANIFEST)
        target = next(l for l in state if l["name"] == "jules")
        target["name"] = "Jules"  # differs only in case — must update, not duplicate
        p, a = self.run_sync(state)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse(a["create"], "a case-only difference must not create a duplicate")
        self.assertIn("Jules", a["update"])
        self.assertEqual(a["update"]["Jules"]["new_name"], "jules")


class ManifestValidationTest(unittest.TestCase):
    def _write(self, obj):
        path = os.path.join(tempfile.mkdtemp(), "labels.json")
        with open(path, "w") as f:
            json.dump(obj, f)
        return path

    def test_real_manifest_is_valid(self):
        labels = sync_labels.load_manifest(os.path.join(ROOT, "labels.json"))
        self.assertTrue(labels)
        names = [l["name"] for l in labels]
        self.assertEqual(len(names), len(set(names)), "manifest names are unique")

    def test_rejects_bad_color(self):
        path = self._write({"labels": [
            {"name": "x", "color": "#1d76db", "description": "hash not allowed"}]})
        with self.assertRaises(SystemExit):
            sync_labels.load_manifest(path)

    def test_rejects_duplicate_name(self):
        path = self._write({"labels": [
            {"name": "dup", "color": "1d76db", "description": "a"},
            {"name": "DUP", "color": "0e8a16", "description": "b"}]})
        with self.assertRaises(SystemExit):
            sync_labels.load_manifest(path)

    def test_rejects_missing_name(self):
        path = self._write({"labels": [{"color": "1d76db", "description": "no name"}]})
        with self.assertRaises(SystemExit):
            sync_labels.load_manifest(path)

    def test_rejects_empty(self):
        path = self._write({"labels": []})
        with self.assertRaises(SystemExit):
            sync_labels.load_manifest(path)

    def test_rejects_overlong_description(self):
        path = self._write({"labels": [
            {"name": "x", "color": "1d76db", "description": "z" * 101}]})
        with self.assertRaises(SystemExit):
            sync_labels.load_manifest(path)

    def test_missing_manifest_is_clean_exit(self):
        with self.assertRaises(SystemExit):
            sync_labels.load_manifest("/nonexistent/labels.json")


if __name__ == "__main__":
    unittest.main()
