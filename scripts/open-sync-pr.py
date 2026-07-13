#!/usr/bin/env python3
"""Propagate concord-owned files into one member repo via a pull request.

Branch-protected members reject direct commits to their default branch, so we
stage all concord-owned changes on a `concord-sync` branch and open (or update)
a single PR. Idempotent: the branch is reset to the default-branch head each run
and the desired files re-applied, so re-running with no upstream change produces
no PR (and an open PR just gets refreshed).

Concord-owned payloads synced here:
  - everything under propagate/  (e.g. .github/ISSUE_TEMPLATE/*.yml and
    versions-common.properties, the suite toolchain pins)
  - AGENTS.md and .gitignore, but only their concord:* regions, and only if the
    member already carries the markers (unseeded repos are left untouched).
  - .ai/skills/** and .ai/commands/** — the vendored skills and slash commands,
    wholly concord-owned. Mirrors `make sync`'s `rsync -a --delete`: the
    git-tracked concord tree is the source of truth, and member files under those
    prefixes that concord no longer ships are removed. The
    .ai/skills/.concord-rev provenance file records the concord commit the branch
    was staged from, and bumps only when skill/command content moves.

How the diff is computed
------------------------
The member's whole default-branch tree is fetched ONCE (recursive), giving a
{path: blob_sha} map. A file needs writing iff the git blob SHA of the content
concord wants to stage differs from the member's blob SHA at that path — computed
locally, so the only per-file network calls are the two region-merge reads
(AGENTS.md, .gitignore). This keeps each member to a handful of API calls instead
of one `contents` GET per vendored file, which is what tripped GitHub's secondary
rate limit when every member ran at once.

Every `gh` call is retried with capped exponential backoff, and responses are
parsed as JSON in-process — a throttled or malformed response is retried, never
piped into a filter that would abort the run. If the member tree comes back
truncated we bail rather than risk staging wrong deletions from a partial view.

Usage:  scripts/open-sync-pr.py <owner/repo>
Env:    GH_TOKEN with Contents: write + Pull requests: write on the member.
Run from the concord repo root. GITHUB_SHA labels the commits and stamps
.concord-rev (falls back to the local HEAD sha outside Actions).
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time

BRANCH = "concord-sync"

# Retry policy for `gh`. The failure we hardened against is GitHub's secondary
# rate limit under the concurrent all-members run — transient, so back off and
# retry rather than abort. Overridable via env for fast, sleepless tests.
MAX_ATTEMPTS = int(os.environ.get("SYNC_PR_MAX_ATTEMPTS", "5"))
BACKOFF_BASE = float(os.environ.get("SYNC_PR_BACKOFF_BASE", "2"))
BACKOFF_CAP = float(os.environ.get("SYNC_PR_BACKOFF_CAP", "60"))

# The vendored trees concord owns wholesale (mirrored with --delete semantics).
VENDORED_PREFIXES = (".ai/skills/", ".ai/commands/")
CONCORD_REV = ".ai/skills/.concord-rev"


def _run(argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True)


def _looks_not_found(text: str) -> bool:
    low = text.lower()
    return "not found" in low or "404" in text


def gh(
    endpoint: str,
    *,
    method: str | None = None,
    fields: dict[str, str] | None = None,
    allow_missing: bool = False,
):
    """Call `gh api`, returning the parsed JSON response.

    Retries transient failures (rate limits, 5xx, malformed bodies) with capped
    exponential backoff. `allow_missing` turns a 404 into a None return instead
    of an error — used for optional reads (does this ref/file exist yet?).
    """
    argv = ["gh", "api", endpoint]
    if method:
        argv += ["-X", method]
    for key, value in (fields or {}).items():
        argv += ["-f", f"{key}={value}"]

    last = ""
    for attempt in range(MAX_ATTEMPTS):
        proc = _run(argv)
        if proc.returncode == 0:
            body = proc.stdout.strip()
            if not body:
                return {}
            try:
                return json.loads(body)
            except json.JSONDecodeError as err:
                last = f"invalid JSON response: {err}"  # transient — retry
        else:
            combined = proc.stdout + proc.stderr
            if allow_missing and _looks_not_found(combined):
                return None
            last = combined.strip() or f"gh exited {proc.returncode}"
        if attempt + 1 < MAX_ATTEMPTS:
            delay = min(BACKOFF_CAP, BACKOFF_BASE * (2 ** attempt))
            print(f"  retry ({attempt + 1}/{MAX_ATTEMPTS}) {endpoint}: {last}", file=sys.stderr)
            time.sleep(delay)
    raise SystemExit(f"gh api {endpoint} failed after {MAX_ATTEMPTS} attempts: {last}")


def gh_pr(argv: list[str]) -> subprocess.CompletedProcess:
    """Run a `gh pr ...` subcommand with the same retry policy."""
    last = ""
    for attempt in range(MAX_ATTEMPTS):
        proc = _run(["gh", *argv])
        if proc.returncode == 0:
            return proc
        last = (proc.stdout + proc.stderr).strip() or f"gh exited {proc.returncode}"
        if attempt + 1 < MAX_ATTEMPTS:
            delay = min(BACKOFF_CAP, BACKOFF_BASE * (2 ** attempt))
            print(f"  retry ({attempt + 1}/{MAX_ATTEMPTS}) gh {argv[0]}: {last}", file=sys.stderr)
            time.sleep(delay)
    raise SystemExit(f"gh {' '.join(argv)} failed after {MAX_ATTEMPTS} attempts: {last}")


def git_blob_sha(data: bytes) -> str:
    """The git object id git would assign this blob — matches `git hash-object`."""
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def git_tracked(*paths: str) -> list[str]:
    out = _run(["git", "ls-files", *paths]).stdout.split("\n")
    return [p for p in out if p]


def inject_regions(source: str, content: bytes) -> bytes | None:
    """Rewrite the concord:* regions of `content` from `source`, or None on failure.

    Delegates to inject-agents-regions.py so the region grammar lives in one
    place. A member with no markers comes back unchanged (the inject is inert),
    which the caller sees as "no diff".
    """
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        proc = _run(["python3", "scripts/inject-agents-regions.py", source, tmp_path])
        if proc.returncode != 0:
            return None
        with open(tmp_path, "rb") as handle:
            return handle.read()
    finally:
        os.unlink(tmp_path)


def fetch_file(repo: str, ref: str, path: str) -> bytes | None:
    """Fetch a member file's bytes via the contents API, or None if absent."""
    resp = gh(f"repos/{repo}/contents/{path}?ref={ref}", allow_missing=True)
    if not isinstance(resp, dict) or resp.get("encoding") != "base64":
        return None
    return base64.b64decode(resp["content"])


def build_desired(repo: str, default: str, tree: dict[str, str]) -> dict[str, bytes]:
    """Map dest path in the member -> the exact bytes concord wants to stage."""
    desired: dict[str, bytes] = {}

    # propagate/* — verbatim concord-owned files, at the same relative path.
    propagate = os.path.join(os.getcwd(), "propagate")
    for root, _dirs, files in os.walk(propagate):
        for name in files:
            src = os.path.join(root, name)
            dest = os.path.relpath(src, propagate)
            with open(src, "rb") as handle:
                desired[dest] = handle.read()

    # .ai/skills/** and .ai/commands/** — the git-tracked set (never the working
    # tree) so build caches like __pycache__ are excluded; the working-tree file
    # is the content source, matching what `make sync` rsyncs.
    for src in git_tracked(".ai/skills", ".ai/commands"):
        with open(src, "rb") as handle:
            desired[src] = handle.read()

    # AGENTS.md / .gitignore region merges — only for members that carry the file
    # (i.e. it appears in the tree). inject leaves an un-seeded file untouched, so
    # the result simply shows no diff.
    for path, source in (("AGENTS.md", "AGENTS-COMMON.md"), (".gitignore", "gitignore-common")):
        if path not in tree:
            continue
        current = fetch_file(repo, default, path)
        if current is None:
            continue
        merged = inject_regions(source, current)
        if merged is None:
            print(f"  warn: skipping {path} for {repo} (inject failed)", file=sys.stderr)
            continue
        desired[path] = merged

    return desired


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    repo = argv[0]

    src_sha = os.environ.get("GITHUB_SHA")
    if not src_sha:
        head = _run(["git", "rev-parse", "HEAD"])
        src_sha = head.stdout.strip() if head.returncode == 0 else "local"
    short = src_sha[:7]

    default = gh(f"repos/{repo}")["default_branch"]
    head_sha = gh(f"repos/{repo}/git/ref/heads/{default}")["object"]["sha"]

    # The member's whole default-branch tree, once. This backs BOTH the diff (does
    # each desired file already match?) and the --delete pass (which vendored
    # blobs did concord drop?). A truncated tree is a partial view — staging
    # deletions off it could remove files that are really still shipped, so bail.
    tree_sha = gh(f"repos/{repo}/git/commits/{head_sha}")["tree"]["sha"]
    tree_resp = gh(f"repos/{repo}/git/trees/{tree_sha}?recursive=1")
    if tree_resp.get("truncated"):
        raise SystemExit(f"{repo}: default-branch tree came back truncated; refusing to sync")
    tree = {e["path"]: e["sha"] for e in tree_resp["tree"] if e.get("type") == "blob"}

    desired = build_desired(repo, default, tree)

    # Which desired files differ from the member? Compare blob ids locally.
    changed: list[str] = []
    base_sha: dict[str, str | None] = {}
    for dest, data in desired.items():
        base_sha[dest] = tree.get(dest)
        if git_blob_sha(data) != tree.get(dest):
            changed.append(dest)

    # --delete semantics for the vendored trees: any member blob under a vendored
    # prefix that concord no longer ships is removed. .concord-rev is
    # concord-generated (concord itself does not carry it), so never a candidate.
    deleted: list[str] = []
    del_sha: dict[str, str] = {}
    for path, sha in tree.items():
        if path == CONCORD_REV:
            continue
        if path.startswith(VENDORED_PREFIXES) and path not in desired:
            deleted.append(path)
            del_sha[path] = sha

    # Did any vendored content move (add/update/remove)? The .concord-rev stamp
    # bumps only then — an AGENTS.md-only sync leaves the vendored tree, and its
    # recorded revision, untouched.
    def is_vendored(path: str) -> bool:
        return path.startswith(VENDORED_PREFIXES)

    skills_touched = any(is_vendored(p) for p in (*changed, *deleted))

    if not changed and not deleted:
        print(f"{repo}: up to date — no PR needed")
        return 0

    # Stamp .ai/skills/.concord-rev with the concord commit the branch is staged
    # from, but only when the vendored content moved (otherwise the file, and the
    # PR, would churn on every unrelated concord change).
    if skills_touched:
        rev_data = (src_sha + "\n").encode()
        if git_blob_sha(rev_data) != tree.get(CONCORD_REV):
            desired[CONCORD_REV] = rev_data
            base_sha[CONCORD_REV] = tree.get(CONCORD_REV)
            changed.append(CONCORD_REV)

    print(f"{repo}: {len(changed)} to write, {len(deleted)} to remove: "
          f"{' '.join(changed)} {' '.join(deleted)}".rstrip())

    # Reset the sync branch to the current default head (create if missing), so
    # each run starts clean and the PR diff is exactly concord's desired changes.
    if gh(f"repos/{repo}/git/ref/heads/{BRANCH}", allow_missing=True) is not None:
        gh(f"repos/{repo}/git/refs/heads/{BRANCH}", method="PATCH",
           fields={"sha": head_sha, "force": "true"})
    else:
        gh(f"repos/{repo}/git/refs", method="POST",
           fields={"ref": f"refs/heads/{BRANCH}", "sha": head_sha})

    # Apply each changed file. After the reset a file's sha on the branch equals
    # its sha on default, so base_sha is the right precondition; new files carry
    # no sha.
    for dest in changed:
        fields = {
            "message": f"chore: sync {dest} from concord@{short}",
            "content": base64.b64encode(desired[dest]).decode(),
            "branch": BRANCH,
        }
        if base_sha.get(dest):
            fields["sha"] = base_sha[dest]
        gh(f"repos/{repo}/contents/{dest}", method="PUT", fields=fields)
        print(f"  staged: {dest}")

    # Remove member files concord dropped. After the reset the branch blob sha
    # equals the default-branch sha captured above, so del_sha is the precondition.
    for dest in deleted:
        gh(f"repos/{repo}/contents/{dest}", method="DELETE",
           fields={"message": f"chore: sync (remove {dest}) from concord@{short}",
                   "sha": del_sha[dest], "branch": BRANCH})
        print(f"  removed: {dest}")

    # Open the PR if one isn't already open for this branch.
    listing = gh_pr(["pr", "list", "-R", repo, "--head", BRANCH, "--state", "open", "--json", "number"])
    existing = json.loads(listing.stdout or "[]")
    if existing:
        print(f"{repo}: refreshed existing PR #{existing[0]['number']}")
    else:
        gh_pr([
            "pr", "create", "-R", repo, "--base", default, "--head", BRANCH,
            "--title", "chore: sync concord-owned files",
            "--body",
            f"Automated sync from concord@{short} (issue templates, "
            "versions-common.properties suite toolchain pins, AGENTS.md + "
            ".gitignore shared regions, vendored .ai/skills + .ai/commands). "
            "Generated by propagate.yml — merge to adopt; the branch refreshes on "
            "each concord change.",
        ])
        print(f"{repo}: opened PR")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
