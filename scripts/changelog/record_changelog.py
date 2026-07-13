#!/usr/bin/env python3
"""Record a published release's notes into changelogs/<version>.md.

The terminal, best-effort step of the reusable release workflow
(.github/workflows/mod-release.yml). It mirrors the exact published body
(the same /tmp/release-body.md sent to GitHub / Modrinth / CurseForge) into
changelogs/<version>.md on the default branch, so the repo keeps a complete
Markdown record of every release — hand-written or AI-generated. The website
changelog derives from changelogs/* plus GitHub Releases, so recording the AI
notes here keeps the in-repo history complete.

Member default branches require a pull request (0 approvals, 0 checks), so a
direct push is impossible: the file is staged on a changelog/vX.Y.Z branch via
the Contents API (the same mechanism as open-sync-pr.py) and the PR is merged
with GITHUB_TOKEN — no branch-protection bypass and no extra secret.

Idempotent. It no-ops when the version is already recorded: a hand-authored file
shipped with the tag (present in the checkout), or a prior run already committed
it (present on the default branch). Stdlib only — no pip install, so it runs on
the system python3 without setup-python.

Env:
  GITHUB_TOKEN       token with contents:write + pull-requests:write
  GITHUB_REPOSITORY  owner/repo (set by Actions)
  VERSION            release version, no leading v (e.g. 1.2.0)
  CHANGELOG_FILE     path to the published body (default /tmp/release-body.md)
  CHANGELOGS_DIR     directory for records (default changelogs)
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://api.github.com"
MERGE_ATTEMPTS = 6
MERGE_WAIT_S = 5


def log(msg: str) -> None:
    print(msg, flush=True)


def notice(msg: str) -> None:
    print(f"::notice::{msg}", flush=True)


def warn(msg: str) -> None:
    print(f"::warning::{msg}", flush=True)


def env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    return v if v not in (None, "") else default


def api(method: str, path: str, token: str, body: dict | None = None):
    """Call the GitHub REST API. Returns (status, parsed-json-or-{})."""
    url = path if path.startswith("http") else f"{API}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            payload = json.loads(raw) if raw else {}
        except ValueError:
            payload = {"message": raw.decode(errors="replace")}
        return e.code, payload


def main() -> int:
    token = env("GITHUB_TOKEN")
    repo = env("GITHUB_REPOSITORY")
    version = env("VERSION")
    body_file = env("CHANGELOG_FILE", "/tmp/release-body.md")
    cl_dir = env("CHANGELOGS_DIR", "changelogs")

    if not (token and repo and version):
        warn("record_changelog: missing GITHUB_TOKEN / GITHUB_REPOSITORY / VERSION")
        return 0
    if not os.path.isfile(body_file) or os.path.getsize(body_file) == 0:
        notice("no release body to record")
        return 0

    dest = f"{cl_dir}/{version}.md"

    # A hand-authored file shipped with the tag — leave it, nothing to record.
    if os.path.exists(dest):
        notice(f"{dest} shipped with the tag; already recorded")
        return 0

    status, repo_info = api("GET", f"/repos/{repo}", token)
    if status != 200:
        warn(f"could not read repo metadata ({status}); skipping record")
        return 0
    default = repo_info.get("default_branch", "master")

    # Already on the default branch from a prior run — idempotent no-op.
    status, _ = api("GET", f"/repos/{repo}/contents/{dest}?ref={default}", token)
    if status == 200:
        notice(f"{dest} already on {default}; nothing to record")
        return 0

    status, ref = api("GET", f"/repos/{repo}/git/ref/heads/{default}", token)
    if status != 200:
        warn(f"could not resolve {default} head ({status}); skipping record")
        return 0
    head_sha = ref["object"]["sha"]

    # Stage the file on a fresh branch reset to the default head.
    branch = f"changelog/v{version}"
    status, _ = api("GET", f"/repos/{repo}/git/ref/heads/{branch}", token)
    if status == 200:
        api("PATCH", f"/repos/{repo}/git/refs/heads/{branch}", token,
            {"sha": head_sha, "force": True})
    else:
        api("POST", f"/repos/{repo}/git/refs", token,
            {"ref": f"refs/heads/{branch}", "sha": head_sha})

    with open(body_file, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode()
    status, put = api("PUT", f"/repos/{repo}/contents/{dest}", token, {
        "message": f"docs(changelog): record v{version} release notes [skip ci]",
        "content": content_b64,
        "branch": branch,
    })
    if status not in (200, 201):
        warn(f"could not stage {dest} ({status}): {put.get('message')}")
        return 0

    # Open the PR, or reuse an existing one left by a prior partial run.
    owner = repo.split("/")[0]
    status, pr = api("POST", f"/repos/{repo}/pulls", token, {
        "title": f"docs(changelog): record v{version} release notes",
        "head": branch,
        "base": default,
        "body": (f"Mirrors the published v{version} notes into `{cl_dir}/` so the "
                 "repo keeps the same record shipped to GitHub, Modrinth, and "
                 "CurseForge. Opened by mod-release.yml; safe to merge as-is."),
    })
    if status in (200, 201):
        number = pr["number"]
    elif status == 422:  # a PR for this head already exists
        _, prs = api(
            "GET", f"/repos/{repo}/pulls?head={owner}:{branch}&state=open", token)
        if not prs:
            warn(f"could not open or find a PR for {branch}")
            return 0
        number = prs[0]["number"]
    else:
        warn(f"could not open PR for {branch} ({status}): {pr.get('message')}")
        return 0

    # master needs 0 approvals / 0 checks, so the PR is mergeable almost at once;
    # retry to absorb GitHub's async mergeability computation (405 until ready).
    for _ in range(MERGE_ATTEMPTS):
        status, _ = api("PUT", f"/repos/{repo}/pulls/{number}/merge", token, {
            "merge_method": "squash",
            "commit_title": f"docs(changelog): record v{version} release notes [skip ci]",
        })
        if status == 200:
            log(f"✅ Recorded {dest} on {default} (PR #{number})")
            api("DELETE", f"/repos/{repo}/git/refs/heads/{branch}", token)
            return 0
        time.sleep(MERGE_WAIT_S)

    warn(f"opened changelog PR #{number} for v{version} but could not auto-merge "
         "it — merge it manually")
    return 0


if __name__ == "__main__":
    sys.exit(main())
