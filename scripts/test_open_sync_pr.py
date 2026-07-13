#!/usr/bin/env python3
"""Integration tests for scripts/open-sync-pr.py.

The script proposes concord-owned files onto each member's `concord-sync` PR by
calling `gh`. These tests drive it against a mock `gh` that serves a synthetic
member repo and records the mutating calls, then assert the sync semantics that
matter for the vendored .ai/skills / .ai/commands trees:

  A. drift        — a missing skill is created, a stale one updated, a
                    concord-dropped one deleted, and .concord-rev bumped once.
  B. in sync      — nothing to do → no PR, and .concord-rev does not churn.
  C. non-skill    — a stale issue template opens a PR, but .concord-rev is NOT
                    bumped (its stamp tracks the vendored tree, nothing else).

The script diffs by comparing each desired file's git blob SHA against the
member's default-branch tree, so the mock serves that tree with real
`git hash-object` blob ids and drift is expressed by perturbing a path's tree
SHA — exactly how a genuinely divergent member would present.
"""
import base64
import json
import os
import subprocess
import tempfile
import unittest

ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                      capture_output=True, text=True, check=True).stdout.strip()
GH_SHA = "abc1234def5678" + "0" * 26  # 40-char fake concord commit

# A standalone `gh` replacement. Serves the member described by $MEMBER_STATE and
# appends each mutating call to $ACTIONS_LOG as one JSON object per line.
GH_MOCK = r'''#!/usr/bin/env python3
import base64, json, os, subprocess, sys, urllib.parse
STATE = json.load(open(os.environ["MEMBER_STATE"]))
def log(a):
    open(os.environ["ACTIONS_LOG"], "a").write(json.dumps(a) + "\n")
def emit(obj, q):
    text = json.dumps(obj)
    if q is None:
        sys.stdout.write(text); return
    p = subprocess.run(["jq", "-r", q], input=text, capture_output=True, text=True)
    sys.stdout.write("" if p.stdout.strip() == "null" else p.stdout)
def parse(argv):
    method, endpoint, q, fields = "GET", None, None, {}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "-X": method = argv[i+1]; i += 2; continue
        if a == "-q": q = argv[i+1]; i += 2; continue
        if a in ("-f", "-F"):
            k, _, v = argv[i+1].partition("="); fields[k] = v; i += 2; continue
        if endpoint is None and not a.startswith("-"): endpoint = a
        i += 1
    return method, endpoint, q, fields
def main():
    argv = sys.argv[1:]
    if argv and argv[0] == "pr":
        if "list" in argv:
            emit([], next((argv[i+1] for i, a in enumerate(argv) if a == "-q"), None)); return
        if "create" in argv:
            log({"action": "pr_create"}); sys.stdout.write("https://example/pr/1\n"); return
        return
    method, endpoint, q, fields = parse(argv[1:])
    repo = STATE["repo"]
    if endpoint == f"repos/{repo}":
        emit({"default_branch": STATE["default_branch"]}, q); return
    if "/git/refs" in endpoint and method == "POST":
        log({"action": "create_ref"}); emit({}, q); return
    if "/git/refs/heads/" in endpoint and method == "PATCH":
        log({"action": "update_ref"}); emit({}, q); return
    if "/git/ref/heads/" in endpoint:
        emit({"object": {"sha": STATE["head_sha"]}}, q); return
    if "/git/commits/" in endpoint:
        emit({"tree": {"sha": STATE["tree_sha"]}}, q); return
    if "/git/trees/" in endpoint:
        tree = [{"path": p, "sha": s, "type": "blob"} for p, s in STATE["tree"].items()]
        emit({"tree": tree, "truncated": False}, q); return
    if "/contents/" in endpoint:
        key = urllib.parse.unquote(endpoint.split("/contents/", 1)[1].split("?", 1)[0])
        if method == "PUT":
            log({"action": "put", "path": key,
                 "content": base64.b64decode(fields["content"]).decode("utf-8", "replace"),
                 "has_sha": "sha" in fields}); emit({"content": {}}, q); return
        if method == "DELETE":
            log({"action": "delete", "path": key, "sha": fields.get("sha")}); emit({}, q); return
        f = STATE["contents"].get(key)
        if f is None:
            sys.stdout.write(json.dumps({"message": "Not Found"})); sys.exit(1)
        emit({"encoding": "base64",
              "content": base64.b64encode(f["content"].encode()).decode() + "\n",
              "sha": f["sha"]}, q); return
    sys.stderr.write("gh mock: unhandled " + str(endpoint) + "\n"); sys.exit(3)
main()
'''


def _tracked(*dirs):
    out = subprocess.run(["git", "-C", ROOT, "ls-files", *dirs],
                         capture_output=True, text=True).stdout.split()
    return [p for p in out if p]


def _blob_sha(path):
    return subprocess.run(["git", "-C", ROOT, "hash-object", path],
                          capture_output=True, text=True).stdout.strip()


def _synced_member():
    """A member fully in sync with concord: matching skills/commands + templates."""
    contents, tree = {}, {}
    for p in _tracked(".ai/skills", ".ai/commands"):
        text = open(os.path.join(ROOT, p), encoding="utf-8").read()
        sha = _blob_sha(p)
        contents[p] = {"content": text, "sha": sha}
        tree[p] = sha
    tree[".ai/skills/.concord-rev"] = "revsha"
    contents[".ai/skills/.concord-rev"] = {"content": GH_SHA + "\n", "sha": "revsha"}
    for p in _tracked("propagate"):
        dest = p[len("propagate/"):]
        sha = _blob_sha(os.path.join(ROOT, p))
        contents[dest] = {"content": open(os.path.join(ROOT, p), encoding="utf-8").read(),
                          "sha": sha}
        tree[dest] = sha
    return {"repo": "rfizzle/testmember", "default_branch": "master",
            "head_sha": "deadbeef" * 5, "tree_sha": "cafef00d" * 5,
            "contents": contents, "tree": tree}


class OpenSyncPRTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.gh = os.path.join(self.tmp, "gh")
        with open(self.gh, "w") as f:
            f.write(GH_MOCK)
        os.chmod(self.gh, 0o755)

    def run_sync(self, state):
        state_path = os.path.join(self.tmp, "member_state.json")
        log_path = os.path.join(self.tmp, "actions.log")
        with open(state_path, "w") as f:
            json.dump(state, f)
        if os.path.exists(log_path):
            os.remove(log_path)
        env = dict(os.environ)
        env["PATH"] = self.tmp + os.pathsep + env["PATH"]
        env["MEMBER_STATE"] = state_path
        env["ACTIONS_LOG"] = log_path
        env["GITHUB_SHA"] = GH_SHA
        env["GH_TOKEN"] = "x"
        p = subprocess.run(["python3", "scripts/open-sync-pr.py", "rfizzle/testmember"],
                           cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, f"script failed:\n{p.stdout}\n{p.stderr}")
        if os.path.exists(log_path):
            with open(log_path) as f:
                actions = [json.loads(l) for l in f]
        else:
            actions = []
        return p.stdout.strip(), {
            "put": {a["path"]: a for a in actions if a["action"] == "put"},
            "delete": {a["path"]: a for a in actions if a["action"] == "delete"},
            "pr": [a for a in actions if a["action"] == "pr_create"],
        }

    def test_drift_creates_updates_deletes_and_bumps_rev(self):
        st = _synced_member()
        create, update = ".ai/commands/glyph.md", ".ai/skills/CATALOG.md"
        stale = ".ai/skills/mc-obsolete/SKILL.md"
        del st["contents"][create], st["tree"][create]        # member missing -> create
        st["tree"][update] = "driftsha"                        # member stale -> update
        st["tree"][stale] = "stalesha"                          # concord dropped -> delete
        st["contents"][stale] = {"content": "x", "sha": "stalesha"}
        st["contents"][".ai/skills/.concord-rev"]["content"] = "0" * 40 + "\n"

        _, a = self.run_sync(st)
        self.assertIn(create, a["put"])
        self.assertFalse(a["put"][create]["has_sha"], "new file must PUT without a base sha")
        self.assertIn(update, a["put"])
        self.assertTrue(a["put"][update]["has_sha"], "update must PUT with the base sha")
        self.assertEqual(a["put"].get(".ai/skills/.concord-rev", {}).get("content"), GH_SHA + "\n")
        self.assertNotIn(".ai/skills/mc-hud/SKILL.md", a["put"], "unchanged skills must not be re-PUT")
        self.assertEqual(a["delete"].get(stale, {}).get("sha"), "stalesha")
        self.assertNotIn(".ai/skills/.concord-rev", a["delete"], ".concord-rev must never be deleted")
        self.assertEqual(len(a["pr"]), 1)

    def test_in_sync_opens_no_pr(self):
        out, a = self.run_sync(_synced_member())
        self.assertFalse(a["put"])
        self.assertFalse(a["delete"])
        self.assertFalse(a["pr"])
        self.assertIn("up to date", out)

    def test_non_skill_change_does_not_bump_rev(self):
        st = _synced_member()
        tmpl = _tracked("propagate")[0][len("propagate/"):]
        st["tree"][tmpl] = "tmpldrift"
        _, a = self.run_sync(st)
        self.assertIn(tmpl, a["put"], "the stale template must be re-staged")
        self.assertNotIn(".ai/skills/.concord-rev", a["put"],
                         ".concord-rev tracks the vendored tree, not unrelated files")
        self.assertFalse(a["delete"])
        self.assertEqual(len(a["pr"]), 1)


if __name__ == "__main__":
    unittest.main()
