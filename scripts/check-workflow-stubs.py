#!/usr/bin/env python3
"""Check each member repo's .github/workflows/*.yml caller stubs against the
canonical contract in workflow-stubs.json.

Member stubs are thin wrappers that `uses:` one of concord's reusable workflows.
The reusable workflows deliberately cap their job tokens, so a stub that grants
extra permissions silently widens what a compromised step can reach. This guard
diffs the fields that must never drift — the `uses:` workflow and its `@<ref>`,
the top-level `permissions:` block, and the `concord-ref` input — against the
canonical manifest, and ignores everything a member is free to vary (the `on:`
triggers, other `with:` inputs like curseforge-id, and concurrency).

Release channels: the manifest's top-level `ref` (stable) is what members call;
its `canary` map (member id -> hub ref) names members that call a different ref
(master). For a reusable workflow that declares a `concord-ref` input (read from
the hub's own .github/workflows/<file>.yml next to the manifest), a canary
member's calling job must pass `with.concord-ref` equal to its ref, so the
workflow and the hub files it loads come from the same ref; any other member
must omit it or pass the default ref.

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


def load_manifest(path: pathlib.Path) -> tuple[list[dict], str, dict]:
    """The stubs list, the default (stable) hub ref, and the canary map."""
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
    ref = data.get("ref")
    if not isinstance(ref, str) or not ref:
        print("error: workflow-stubs.json has no 'ref' string", file=sys.stderr)
        raise SystemExit(2)
    canary = data.get("canary", {})
    if not isinstance(canary, dict) or not all(
        isinstance(v, str) and v for v in canary.values()
    ):
        print("error: workflow-stubs.json 'canary' must map member id -> ref", file=sys.stderr)
        raise SystemExit(2)
    return stubs, ref, canary


def declares_concord_ref(hub_root: pathlib.Path, uses: str) -> bool:
    """Whether the hub's reusable workflow behind `uses` declares a
    `concord-ref` workflow_call input. A workflow missing from the hub tree
    declares nothing."""
    wf = hub_root / ".github" / "workflows" / uses.rsplit("/", 1)[-1]
    try:
        doc = yaml.safe_load(wf.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return False
    if not isinstance(doc, dict):
        return False
    # PyYAML (YAML 1.1) parses the bare key `on` as boolean True.
    on = doc.get("on", doc.get(True))
    call = on.get("workflow_call") if isinstance(on, dict) else None
    inputs = call.get("inputs") if isinstance(call, dict) else None
    return isinstance(inputs, dict) and "concord-ref" in inputs


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


def check_concord_ref(job: dict, ref: str, canary_ref: str | None) -> list[str]:
    """Findings for the calling job's `with.concord-ref`: a canary member must
    pass its ref; any other member must omit it or pass the default ref."""
    with_ = job.get("with")
    found = with_.get("concord-ref") if isinstance(with_, dict) else None
    if canary_ref:
        if found != canary_ref:
            shown = "missing" if found is None else f"'{found}'"
            return [f"with: concord-ref is {shown}, expected '{canary_ref}' (canary)"]
    elif found is not None and found != ref:
        return [f"with: concord-ref is '{found}', expected it omitted or '{ref}'"]
    return []


def check_stub(
    stub: dict,
    wf_path: pathlib.Path,
    ref: str,
    canary_ref: str | None = None,
    has_concord_ref: bool = False,
) -> list[str]:
    """Findings for one member stub file. Empty list means it matches.

    `ref` is the default (stable) hub ref; `canary_ref` is set for a canary
    member and replaces it; `has_concord_ref` is whether the reusable workflow
    declares a `concord-ref` input."""
    if not wf_path.exists():
        return ["missing stub file"]
    try:
        doc = yaml.safe_load(wf_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return [f"malformed YAML: {exc}"]
    if not isinstance(doc, dict):
        return ["malformed stub: top level is not a mapping"]

    want = canary_ref or ref
    expected = f"{stub['uses']}@{want}"
    calls = concord_jobs(doc)
    findings = []
    if not calls:
        findings.append(
            f"uses: no job calls a concord reusable workflow, expected {expected}"
        )
    else:
        for job in calls:
            if job["uses"] != expected:
                findings.append(f"uses: is '{job['uses']}', expected '{expected}'")
            if has_concord_ref:
                findings += check_concord_ref(job, ref, canary_ref)

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

    manifest = pathlib.Path(args.manifest)
    stubs, ref, canary = load_manifest(manifest)
    hub_root = manifest.resolve().parent
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
            has_ref = declares_concord_ref(hub_root, stub["uses"])
            for reason in check_stub(stub, wf_path, ref, canary.get(mid), has_ref):
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
