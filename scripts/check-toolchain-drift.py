#!/usr/bin/env python3
"""Check each member repo's build toolchain pins against concord's canonical
suite toolchain in propagate/versions-common.properties.

Concord owns one set of toolchain pins for the whole suite — the Minecraft
target, Fabric Loader, Fabric API, Loom, and the Java version. They are synced
into each member as versions-common.properties (via the concord-sync PR), and a
member's build reads them by loading that file in settings.gradle. This guard
flags any member whose *effective* pin for a governed key has fallen behind the
canonical value — because the member hasn't merged the sync PR, or is still
pinning the key the old way in gradle.properties.

Effective value, per governed key, uses the same precedence the adopted build
does: the member's versions-common.properties wins if it defines the key,
otherwise the member's gradle.properties. Only a *wrong* value is drift (the
member is behind). A key the member pins nowhere is a note, not drift — it means
the pin isn't sourced from the suite file yet (an adoption gap the properties
files can't distinguish from a value hardcoded in build.gradle), not that the
member is on an old version. A key pinned in both files to *different* values is
also a note: a stale gradle.properties duplicate to drop after adopting the
synced file.

Governed keys come from concord's own propagate/versions-common.properties, so
adding a pin there automatically brings it under this check. Member ids come
from members.json; each member repo is read from <root>/<id>/. Locally that is
the sibling checkout (../<member>, the default); in CI a bash step fetches the
two properties files into a temp mirror and points --root at it.

    python3 scripts/check-toolchain-drift.py            # check ../<member> siblings
    python3 scripts/check-toolchain-drift.py --root DIR # check <DIR>/<member>/...

Exit status: 0 when no checked member is behind (adoption-gap notes still pass);
1 when any member pins a governed key to a stale value; 2 on a missing/malformed
canonical file. Drift and notes print to stderr, one per line, followed by a
summary; a clean run prints a summary to stdout.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys


def parse_properties(text: str) -> dict[str, str]:
    """Parse the subset of the Java .properties format these files use:
    `key=value` (or `key = value`) lines, `#`/`!` comment lines, and blanks. The
    toolchain files carry no line continuations or escapes, so this stays simple
    on purpose — a later key wins, matching Gradle's own load order."""
    props: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line[0] in "#!":
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        props[key.strip()] = value.strip()
    return props


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


def load_canonical(path: pathlib.Path) -> dict[str, str]:
    """The suite toolchain pins concord owns — the governed key set."""
    try:
        pins = parse_properties(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"error: canonical toolchain not found at {path}", file=sys.stderr)
        raise SystemExit(2)
    if not pins:
        print(f"error: {path} defines no toolchain keys", file=sys.stderr)
        raise SystemExit(2)
    return pins


def member_ids(path: pathlib.Path) -> list[str]:
    data = _load_json(path, "members.json")
    return [m["id"] for m in data.get("members", [])]


def _read_props(path: pathlib.Path) -> dict[str, str] | None:
    """Parsed properties, or None if the file is absent."""
    try:
        return parse_properties(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def check_member(
    member_dir: pathlib.Path, canonical: dict[str, str]
) -> tuple[list[str], list[str]]:
    """(drift, notes) for one member. Empty drift means every governed pin
    matches. `member_dir` is <root>/<id>."""
    synced = _read_props(member_dir / "versions-common.properties")
    gradle = _read_props(member_dir / "gradle.properties")
    if synced is None and gradle is None:
        # No pins to read at all — can't compare. Surface it, but it isn't a
        # version lag, so it doesn't fail the check.
        return ([], ["no gradle.properties or versions-common.properties found — cannot compare"])
    synced = synced or {}
    gradle = gradle or {}

    drift: list[str] = []
    notes: list[str] = []
    for key, want in canonical.items():
        in_synced = synced.get(key)
        in_gradle = gradle.get(key)
        # Precedence mirrors the adopted build: the synced file wins if present.
        effective = in_synced if in_synced is not None else in_gradle
        if effective is None:
            notes.append(
                f"{key}: not pinned (expected '{want}') — "
                "adopt the suite pin by loading versions-common.properties in settings.gradle"
            )
        elif effective != want:
            source = "versions-common.properties" if in_synced is not None else "gradle.properties"
            drift.append(f"{key}: {source} pins '{effective}', expected '{want}'")
        elif in_synced is not None and in_gradle is not None and in_gradle != want:
            # Matches via the synced file, but a stale gradle.properties value
            # still shadows it pre-adoption — worth dropping, not drift.
            notes.append(
                f"{key}: gradle.properties still pins '{in_gradle}' "
                "(stale duplicate — drop it once settings.gradle loads versions-common.properties)"
            )
    return (drift, notes)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default="..",
        help="directory holding the member checkouts as <root>/<id> (default: ..)",
    )
    parser.add_argument("--canonical", default="propagate/versions-common.properties")
    parser.add_argument("--members", default="members.json")
    args = parser.parse_args(argv)

    canonical = load_canonical(pathlib.Path(args.canonical))
    ids = member_ids(pathlib.Path(args.members))
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
        member_drift, member_notes = check_member(member_dir, canonical)
        for reason in member_drift:
            drift.append(f"drift: {mid} — {reason}")
        for note in member_notes:
            notes.append(f"note: {mid} — {note}")

    for note in notes:
        print(note, file=sys.stderr)

    if drift:
        for line in drift:
            print(line, file=sys.stderr)
        print(
            f"\n{len(drift)} toolchain drift finding(s) across {checked_members} member(s). "
            "Merge the member's concord-sync PR (or update its pins) to catch up.",
            file=sys.stderr,
        )
        return 1

    if checked_members == 0:
        print("no members checked out — nothing to compare.")
        return 0
    print(
        f"all member toolchains match canonical "
        f"({checked_members} member(s) × {len(canonical)} pin(s))."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
