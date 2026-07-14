#!/usr/bin/env python3
"""Apply concord's shared issue-label manifest to one member repo.

The suite's issue lifecycle (needs-spec -> ready/open-questions -> jules) plus
the cross-mod, exploratory, and triage workflow labels must be identical in
every member repo: same names, colors, and descriptions. labels.json (top-level,
next to members.json) is the single source of truth; this script reconciles one
member to it.

Non-destructive by design: a manifest label is created if the member lacks it
and updated in place when its color or description has drifted. Labels the member
carries that are NOT in the manifest — GitHub's defaults, dependabot's, or any
repo-local label — are left untouched. Nothing is ever deleted.

Idempotent: a label already matching the manifest is skipped, so a second run
with no drift writes nothing. Name matching is case-insensitive (GitHub treats
label names that way), so a label differing only in case is updated in place —
its name recased to the manifest's — rather than duplicated.

Every `gh` call is retried with capped exponential backoff and parsed as JSON
in-process: the labels job fans out across every member at once, the same
concurrent run that trips GitHub's secondary rate limit, so a throttled or
malformed response is retried, never aborted mid-repo.

Usage:  scripts/sync-labels.py <owner/repo>
        scripts/sync-labels.py <owner/repo> --check   # report drift, write nothing
Env:    GH_TOKEN with Issues: write on the member.
Run from the concord repo root (reads ./labels.json).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.parse

MANIFEST = "labels.json"

# Retry policy for `gh`, mirroring open-sync-pr.py. The hardened-against failure
# is GitHub's secondary rate limit under the concurrent all-members matrix run —
# transient, so back off and retry rather than abort. Overridable via env for
# fast, sleepless tests.
MAX_ATTEMPTS = int(os.environ.get("SYNC_LABELS_MAX_ATTEMPTS", "5"))
BACKOFF_BASE = float(os.environ.get("SYNC_LABELS_BACKOFF_BASE", "2"))
BACKOFF_CAP = float(os.environ.get("SYNC_LABELS_BACKOFF_CAP", "60"))


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
    of an error — used for optional reads.
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


def load_manifest(path: str = MANIFEST) -> list[dict[str, str]]:
    """Read and validate labels.json — a bad manifest must fail loudly, not
    silently propagate garbage to every member."""
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    labels = data.get("labels") if isinstance(data, dict) else None
    if not isinstance(labels, list) or not labels:
        raise SystemExit(f"{path}: expected a non-empty 'labels' array")
    seen: set[str] = set()
    for entry in labels:
        if not isinstance(entry, dict):
            raise SystemExit(f"{path}: each label must be an object, got {entry!r}")
        name = entry.get("name")
        color = entry.get("color")
        desc = entry.get("description")
        if not name or not isinstance(name, str):
            raise SystemExit(f"{path}: label missing a name: {entry!r}")
        if name.lower() in seen:
            raise SystemExit(f"{path}: duplicate label name {name!r}")
        seen.add(name.lower())
        if not isinstance(color, str) or len(color) != 6 or any(c not in "0123456789abcdef" for c in color.lower()):
            raise SystemExit(f"{path}: {name!r} color must be a 6-digit hex string without '#', got {color!r}")
        if not isinstance(desc, str):
            raise SystemExit(f"{path}: {name!r} description must be a string")
    return labels


def list_labels(repo: str) -> dict[str, dict]:
    """Every label on the repo, keyed by lower-cased name. Paged manually — the
    gh() helper does not pass --paginate (which would concatenate JSON arrays)."""
    existing: dict[str, dict] = {}
    page = 1
    while True:
        batch = gh(f"repos/{repo}/labels?per_page=100&page={page}")
        if not isinstance(batch, list) or not batch:
            break
        for label in batch:
            existing[label["name"].lower()] = label
        if len(batch) < 100:
            break
        page += 1
    return existing


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("-")]
    check = "--check" in argv
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    repo = args[0]

    manifest = load_manifest()
    existing = list_labels(repo)

    to_create: list[dict[str, str]] = []
    to_update: list[tuple[dict, dict[str, str]]] = []
    for label in manifest:
        current = existing.get(label["name"].lower())
        if current is None:
            to_create.append(label)
            continue
        # Drift if color, description, or exact-case name differs from the manifest.
        if (
            (current.get("color") or "").lower() != label["color"].lower()
            or (current.get("description") or "") != label["description"]
            or current.get("name") != label["name"]
        ):
            to_update.append((current, label))

    if not to_create and not to_update:
        print(f"{repo}: labels in sync — nothing to do")
        return 0

    for label in to_create:
        print(f"{repo}: {'would create' if check else 'create'} {label['name']}")
    for current, label in to_update:
        print(f"{repo}: {'would update' if check else 'update'} {current.get('name')} "
              f"-> {label['name']} ({label['color']})")

    if check:
        return 1  # drift present — a non-zero exit for local CI-style guarding

    for label in to_create:
        gh(f"repos/{repo}/labels", method="POST", fields={
            "name": label["name"], "color": label["color"],
            "description": label["description"]})
    for current, label in to_update:
        name = urllib.parse.quote(current["name"], safe="")
        gh(f"repos/{repo}/labels/{name}", method="PATCH", fields={
            "new_name": label["name"], "color": label["color"],
            "description": label["description"]})

    print(f"{repo}: {len(to_create)} created, {len(to_update)} updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
