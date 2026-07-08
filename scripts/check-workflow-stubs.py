#!/usr/bin/env python3
"""Check each member repo's .github/workflows/*.yml caller stubs against the
canonical contract in workflow-stubs.json.

Member stubs are thin wrappers that `uses:` one of concord's reusable workflows.
The reusable workflows deliberately cap their job tokens, so a stub that grants
extra permissions silently widens what a compromised step can reach. This guard
diffs the two fields that must never drift — the `uses:` ref and the top-level
`permissions:` block — against the canonical manifest, and ignores everything a
member is free to vary (the `on:` triggers, `with:` inputs like curseforge-id,
and concurrency).

Member ids come from members.json; each member repo is read from
<root>/<id>/.github/workflows/<stub>. Locally that is the sibling checkout
(../<member>, the default); in CI a bash step fetches the stubs into a temp
mirror and points --root at it.

    python3 scripts/check-workflow-stubs.py            # check ../<member> siblings
    python3 scripts/check-workflow-stubs.py --root DIR # check <DIR>/<member>/...

Exit status: 0 when every checked stub matches (or no members are checked out);
1 when any drift or malformed stub is found. Drift is printed to stderr, one
finding per line, followed by a summary; a clean run prints a summary to stdout.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import yaml

CONCORD_PREFIX = "rfizzle/concord/.github/workflows/"


def _load_json(path: pathlib.Path, what: str) -> dict:
    """Load a repo-controlled JSON file, failing with a clean message + exit 2
    (never a raw traceback) on a missing or malformed file."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"error: {what} not found at {path}", file=sys.stderr)
        raise SystemExit(2)
    except json.JSONDecodeError as exc:
        print(f"error: {what} is not valid JSON: {exc}", file=sys.stderr)
        raise SystemExit(2)


def load_manifest(path: pathlib.Path) -> list[dict]:
    data = _load_json(path, "workflow-stubs.json")
    stubs = data.get("stubs")
    if not isinstance(stubs, list):
        print("error: workflow-stubs.json has no 'stubs' list", file=sys.stderr)
        raise SystemExit(2)
    for stub in stubs:
        missing = [k for k in ("member", "uses", "permissions") if k not in stub]
        if missing:
            print(
                f"error: workflow-stubs.json entry {stub!r} missing {missing}",
                file=sys.stderr,
            )
            raise SystemExit(2)
    return stubs


def member_ids(path: pathlib.Path) -> list[str]:
    data = _load_json(path, "members.json")
    return [m["id"] for m in data.get("members", [])]


def concord_jobs(doc: dict) -> list[dict]:
    """The stub's jobs that call a concord reusable workflow, in order."""
    jobs = doc.get("jobs")
    if not isinstance(jobs, dict):
        return []
    return [
        job
        for job in jobs.values()
        if isinstance(job, dict)
        and isinstance(job.get("uses"), str)
        and job["uses"].startswith(CONCORD_PREFIX)
    ]


def diff_permissions(expected: dict, found) -> list[str]:
    """Human-readable reasons `found` permissions differ from `expected`."""
    if not isinstance(found, dict):
        shown = "none (no permissions: block)" if found is None else repr(found)
        return [f"permissions: expected {expected}, found {shown}"]
    reasons = []
    for key, val in expected.items():
        if key not in found:
            reasons.append(f"permissions: missing '{key}: {val}'")
        elif found[key] != val:
            reasons.append(
                f"permissions: '{key}' is '{found[key]}', expected '{val}'"
            )
    for key in found:
        if key not in expected:
            reasons.append(f"permissions: unexpected '{key}: {found[key]}' (widens the token)")
    return reasons


def check_stub(stub: dict, wf_path: pathlib.Path) -> list[str]:
    """Findings for one member stub file. Empty list means it matches."""
    if not wf_path.exists():
        return ["missing stub file"]
    try:
        doc = yaml.safe_load(wf_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return [f"malformed YAML: {exc}"]
    if not isinstance(doc, dict):
        return ["malformed stub: top level is not a mapping"]

    calls = concord_jobs(doc)
    findings = []
    if not calls:
        findings.append(
            f"uses: no job calls a concord reusable workflow, expected {stub['uses']}"
        )
    else:
        for job in calls:
            if job["uses"] != stub["uses"]:
                findings.append(f"uses: is '{job['uses']}', expected '{stub['uses']}'")

    # A calling job's own `permissions:` overrides the workflow top-level block
    # for the reusable call, so the effective grant is what must be checked —
    # otherwise a widening moved to job level would slip past.
    if calls and "permissions" in calls[0]:
        effective = calls[0]["permissions"]
    else:
        effective = doc.get("permissions")
    findings += diff_permissions(stub["permissions"], effective)
    return findings


def unknown_concord_stubs(wf_dir: pathlib.Path, known: set[str]) -> list[str]:
    """Member workflow files that call a concord reusable but aren't in the
    manifest — reported as notes so an ungoverned stub is visible, without
    failing the check (a member may legitimately add one before the manifest
    catches up)."""
    if not wf_dir.is_dir():
        return []
    out = []
    for wf in sorted(wf_dir.glob("*.yml")):
        if wf.name in known:
            continue
        if CONCORD_PREFIX in wf.read_text(encoding="utf-8"):
            out.append(wf.name)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default="..",
        help="directory holding the member checkouts as <root>/<id> (default: ..)",
    )
    parser.add_argument("--manifest", default="workflow-stubs.json")
    parser.add_argument("--members", default="members.json")
    args = parser.parse_args(argv)

    stubs = load_manifest(pathlib.Path(args.manifest))
    ids = member_ids(pathlib.Path(args.members))
    known_names = {s["member"] for s in stubs}
    root = pathlib.Path(args.root)

    drift: list[str] = []
    notes: list[str] = []
    checked_members = 0

    for mid in ids:
        member_dir = root / mid
        if not member_dir.is_dir():
            notes.append(f"skip: {mid} not checked out at {member_dir}")
            continue
        checked_members += 1
        wf_dir = member_dir / ".github" / "workflows"
        for stub in stubs:
            wf_path = wf_dir / stub["member"]
            for reason in check_stub(stub, wf_path):
                drift.append(f"drift: {mid}/{stub['member']} — {reason}")
        for name in unknown_concord_stubs(wf_dir, known_names):
            notes.append(
                f"note: {mid}/{name} calls a concord reusable but is not in the manifest"
            )

    for note in notes:
        print(note, file=sys.stderr)

    if drift:
        for line in drift:
            print(line, file=sys.stderr)
        print(
            f"\n{len(drift)} stub drift finding(s) across {checked_members} member(s). "
            "Fix the member stub(s) or update workflow-stubs.json.",
            file=sys.stderr,
        )
        return 1

    if checked_members == 0:
        print("no members checked out — nothing to compare.")
        return 0
    print(
        f"all workflow stubs match canonical "
        f"({checked_members} member(s) × {len(stubs)} stub(s))."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
