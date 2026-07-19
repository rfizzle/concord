#!/usr/bin/env python3
"""Check each member repo's gametest suite is registered from its own manifest.

Fabric gametest entrypoints belong in a gametest-source-set-local
src/gametest/resources/fabric.mod.json, declaring a `<modid>-gametest` mod that
depends on the main mod. Declared in the shipped src/main/resources manifest
instead, they break every dev run set: Loom's dev runtime pulls in
fabric-gametest-api-v1, whose ungated `main` initializer instantiates every
declared entrypoint on launch, and no default run set carries the gametest
source set. A released jar is unaffected — the shipped fabric-api does not
bundle that module — so nothing surfaces until someone runs `runServer`, which
is why this can sit in a repo for months.

The companion manifest also pins its version literally. processResources is
configured for the main source set only, so a `${version}` placeholder in a
manifest another source set owns is copied through untouched and reaches the
loader as that literal string.

What counts as drift, per member:

  - the shipped manifest declares fabric-gametest entrypoints
  - gametest sources exist with no companion manifest to register them
  - the companion manifest's version is an unexpanded placeholder

Everything else is a note: a member with no gametest sources at all, a
companion manifest registering nothing, an id off the `<modid>-gametest`
convention, or a missing dependency on the main mod. Those are worth seeing but
do not fail the run.

Member ids come from members.json; each member repo is read from <root>/<id>/.
Locally that is the sibling checkout (../<member>, the default); in CI a bash
step mirrors each member's manifests and gametest source paths into a temp tree
and points --root at it.

    python3 scripts/check-gametest-manifest.py            # check ../<member> siblings
    python3 scripts/check-gametest-manifest.py --root DIR # check <DIR>/<member>/...

Exit status: 0 when no checked member is misregistered (notes still pass); 1 on
any drift; 2 on a missing/malformed members.json.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

SHIPPED_MANIFEST = pathlib.PurePath("src/main/resources/fabric.mod.json")
COMPANION_MANIFEST = pathlib.PurePath("src/gametest/resources/fabric.mod.json")
GAMETEST_SOURCES = pathlib.PurePath("src/gametest/java")
ENTRYPOINT_KEY = "fabric-gametest"


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


def member_ids(path: pathlib.Path) -> list[str]:
    data = _load_json(path, "members.json")
    return [m["id"] for m in data.get("members", [])]


def _read_manifest(path: pathlib.Path) -> dict | None | str:
    """Parsed manifest, None if absent, or an error string if unparseable.

    A manifest that exists but will not parse is reported rather than skipped:
    treating it as absent would let a syntax error read as "no entrypoints
    here" and pass the check green.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        return f"unparseable: {exc}"


def _entrypoints(manifest: dict) -> list:
    entries = manifest.get("entrypoints")
    if not isinstance(entries, dict):
        return []
    declared = entries.get(ENTRYPOINT_KEY)
    if declared is None:
        return []
    return declared if isinstance(declared, list) else [declared]


def has_gametest_sources(member_dir: pathlib.Path) -> bool:
    sources = member_dir / GAMETEST_SOURCES
    return sources.is_dir() and any(sources.rglob("*.java"))


def check_member(member_dir: pathlib.Path) -> tuple[list[str], list[str]]:
    """(drift, notes) for one member. `member_dir` is <root>/<id>."""
    drift: list[str] = []
    notes: list[str] = []

    shipped = _read_manifest(member_dir / SHIPPED_MANIFEST)
    companion = _read_manifest(member_dir / COMPANION_MANIFEST)
    sources = has_gametest_sources(member_dir)

    if isinstance(shipped, str):
        return ([f"{SHIPPED_MANIFEST} {shipped}"], notes)
    if shipped is None:
        return ([], [f"no {SHIPPED_MANIFEST} found — cannot check"])

    mod_id = shipped.get("id")

    shipped_entries = _entrypoints(shipped)
    if shipped_entries:
        drift.append(
            f"{SHIPPED_MANIFEST} declares {len(shipped_entries)} {ENTRYPOINT_KEY} "
            f"entrypoint(s) — move them to {COMPANION_MANIFEST}, which breaks "
            "every dev run set while they stay here"
        )

    if isinstance(companion, str):
        drift.append(f"{COMPANION_MANIFEST} {companion}")
        return (drift, notes)

    if companion is None:
        if sources:
            drift.append(
                f"gametest sources exist with no {COMPANION_MANIFEST} to register "
                "them — the suite never runs"
            )
        else:
            notes.append("no gametest sources — nothing to register")
        return (drift, notes)

    version = companion.get("version")
    if isinstance(version, str) and "${" in version:
        drift.append(
            f"{COMPANION_MANIFEST} version is '{version}' — processResources does "
            "not expand placeholders for this source set, so pin it literally"
        )

    companion_entries = _entrypoints(companion)
    if not companion_entries and sources:
        notes.append(
            f"{COMPANION_MANIFEST} registers no {ENTRYPOINT_KEY} entrypoints "
            "while gametest sources exist"
        )

    if mod_id:
        expected_id = f"{mod_id}-gametest"
        if companion.get("id") != expected_id:
            notes.append(
                f"{COMPANION_MANIFEST} id is '{companion.get('id')}', "
                f"expected '{expected_id}'"
            )
        depends = companion.get("depends")
        if not isinstance(depends, dict) or mod_id not in depends:
            notes.append(
                f"{COMPANION_MANIFEST} does not depend on '{mod_id}'"
            )

    return (drift, notes)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default="..",
        help="directory holding the member checkouts as <root>/<id> (default: ..)",
    )
    parser.add_argument("--members", default="members.json")
    args = parser.parse_args(argv)

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
        member_drift, member_notes = check_member(member_dir)
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
            f"\n{len(drift)} gametest registration finding(s) across "
            f"{checked_members} member(s). See the mc-mod-testing skill, "
            '"Registering the suite."',
            file=sys.stderr,
        )
        return 1

    if checked_members == 0:
        print("no members checked out — nothing to compare.")
        return 0
    print(f"all member gametest suites register from their own manifest "
          f"({checked_members} member(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
